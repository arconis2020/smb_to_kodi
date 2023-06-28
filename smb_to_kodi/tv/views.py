"""Class-based and function-based view backings for the URLs in the tv app."""
from functools import lru_cache
from random import choice
from pathlib import Path
from lxml import etree, html
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render
from django.urls import reverse
from django.views import generic
from django.utils import timezone

from .models import Player, Library, Series, Episode, Movie
from .kodi import Kodi


class NestedDocument:
    """A representation of a nested set of elements in a document."""

    def __init__(self, shared_root):
        """Set up the basic dictionary to keep track of elements."""
        self.divs = {}  # Elements are added to folders using a key.
        self.shared_root = shared_root

    def add_media_file(self, smb_path, last_watched=None):
        """Add a media file with a smb_path attribute to the correct set of folders."""
        # We'll need the path to be able to get things like file names and parents.
        path = Path(smb_path)
        # Add a button element that will be used with javascript to play this file.
        playbutton = html.HtmlElement("\u25b6")
        playbutton.set("value", smb_path)
        playbutton.set("class", "jsplay")
        playbutton.set("style", "margin: 12px;")
        playbutton.tag = "button"
        # Add the p element, with the button element as a nested element.
        para = etree.Element("p", {"style": "margin: 0;"})
        para.append(playbutton)
        # Add a text span to allow for easier placement:
        txt = etree.Element("span")
        txt.text = path.name
        para.append(txt)
        # Add a last-watched date span to allow for easier placement:
        if bool(last_watched):
            lwe = etree.Element("span", {"style": "color: #3092F5;"})
            lwe.text = f"{last_watched:%Y-%m-%d}"
            para.append(lwe)
        # Add the folder to the divs dict with an appropriate div value.
        folder = path.parent
        res = self.divs.setdefault(folder, etree.Element("div", {"class": "hidable"}))
        # Append the p element to the div/folder where it should live.
        res.append(para)

    @lru_cache(maxsize=4096)
    def _add_folder_to_parent(self, folder, parent):
        """
        Add a folder to a parent, but remember if it's been done.

        As an example of why this is LRU cache is necessary, imagine a folder structure
        like this:
        By Artist/A/{many artists starting with A}

        In this scenario, the stack_folders function is going to try to add the "A" folder
        to the "By Artist" folder as many times as there are songs in the artist folders
        under "A". Only the first attempt to add "A" to "By Artist" makes any sense, and
        the rest are ignored by ElementTree anyway (previous implementations show this),
        so we want to completely skip any action on subsequent adds to speed things up.

        The LRU cache here improves the Music view load time by 2 orders of magnitude
        on my highly nested music collection.
        """
        res = self.divs.setdefault(parent, etree.Element("div", {"class": "hidable"}))
        res.append(self.divs[folder])

    def stack_folders(self):
        """Recurse just once through the folder parents, creating a set of stacked divs."""
        for folder in list(self.divs.keys()):
            while folder != self.shared_root:
                parent = folder.parent
                self._add_folder_to_parent(folder, parent)
                folder = parent

    def sort_and_add_buttons(self):
        """Sort the document in place and then add the collapsible buttons."""
        # Sort the element tree with divs first, then p's, at each level.
        for parent in self.divs[self.shared_root].xpath("//*[./*]"):
            parent[:] = sorted(parent, key=lambda x: x.tag)
        # Use the fact that we can address each folder to add a collapsible button to each folder.
        for key, element in self.divs.items():
            if key == self.shared_root:
                continue
            button = etree.Element("button", {"class": "collapsible"})
            button.text = Path(key).name
            element.addprevious(button)


class IndexView(generic.ListView):
    """Main index view for the /tv/ route."""

    template_name = "tv/index.html"

    def get_context_data(self, **kwargs):
        """Add page context items for better rendering."""
        context = super().get_context_data(**kwargs)
        context["current_player"] = Player.objects.get(pk=1).address if Player.objects.count() == 1 else ""
        context["content_types"] = Library.ContentType.choices
        return context

    def get_queryset(self):
        """Return the list of current libraries in sorted order."""
        return Library.objects.order_by("path")


class SeriesView(generic.ListView):
    """View the list of all series in a current library."""

    def get_context_data(self, **kwargs):
        """Add page context items for better rendering."""
        context = super().get_context_data(**kwargs)
        context["library_shortname"] = self.kwargs["shortname"]
        (
            context["active_series_list"],
            context["new_series_list"],
            context["complete_series_list"],
        ) = Library.objects.get(shortname=self.kwargs["shortname"]).get_series_by_state()
        context["current_player"] = Player.objects.get(pk=1).address if Player.objects.count() == 1 else ""
        return context

    def get_queryset(self):
        """Return the list of current series in this library in sorted order."""
        this_sn = self.kwargs["shortname"]
        libcheck = Library.objects.filter(shortname=this_sn).count()
        if libcheck > 0:
            return Series.objects.filter(library__shortname=this_sn).order_by("series_name")
        raise Http404("No library of that name is loaded in the DB.")


def series_detail(request, shortname, series):
    """View the episode control page for a single series."""
    this_series = Episode.objects.filter(series=series).order_by("smb_path")
    # Enable an automatic "lazy" load on first access.
    if this_series.count() == 0:
        Series.objects.get(pk=series).add_all_episodes()
    unwatched = this_series.filter(watched=False).order_by("smb_path")
    next_episode = unwatched[0] if bool(unwatched) else "No episodes loaded"
    random_episode = choice(unwatched) if bool(unwatched) else "No episodes loaded"
    current_passthrough = Kodi().get_audio_passthrough()
    return render(
        request,
        "tv/series_detail.html",
        {
            "next_episode": next_episode,
            "random_episode": random_episode,
            "series_name": series,
            "shortname": shortname,
            "eplist": this_series,
            "passthrough_state": current_passthrough,
        },
    )


def build_nested_view(library, object_list):
    """Build a nested view for use in both movie and music views."""
    # All media files have a single shared root folder at the library level.
    shared_root = Path(library.get_smb_path(library.path))
    doc = NestedDocument(shared_root)
    for obj in object_list:
        lwn = getattr(obj, "last_watched", None)
        doc.add_media_file(obj.smb_path, lwn)
    doc.stack_folders()
    doc.sort_and_add_buttons()
    # Rendering the content this way allows proper sorting, as opposed to using the templates.
    return etree.tostring(doc.divs[shared_root], encoding="unicode", pretty_print=True)


def music_view(request, shortname):
    """View the music list page with custom collapsibles."""
    this_library = Library.objects.get(shortname=shortname)
    this_song_list = this_library.song_set.all().order_by("smb_path")
    rendered_content = build_nested_view(this_library, this_song_list)
    return render(request, "tv/movie_list.html", {"rendered_content": rendered_content, "library": this_library})


def movie_view(request, shortname):
    """View the movie list page with custom collapsibles."""
    this_library = Library.objects.get(shortname=shortname)
    this_movie_list = this_library.movie_set.all().order_by("smb_path")
    rendered_content = build_nested_view(this_library, this_movie_list)
    return render(request, "tv/movie_list.html", {"rendered_content": rendered_content, "library": this_library})


def play(request, shortname=None, series=None):
    """Play the given file in Kodi (POST target)."""
    mypath = request.POST["smb_path"]
    k = Kodi()
    k.add_and_play(mypath)
    if k.confirm_successful_play(mypath):
        # We want to mark either the episode or the movie as played.
        try:
            this_episode = Episode.objects.get(pk=mypath)
            this_episode.watched = True
            this_episode.save()
        except Episode.DoesNotExist:  # pragma: no cover
            try:
                this_movie = Movie.objects.get(pk=mypath)
            except Movie.DoesNotExist:  # pragma: no cover
                return HttpResponseRedirect(request.META["HTTP_REFERER"])  # pragma: no cover - safe fallback only.
            this_movie.last_watched = timezone.now()
            this_movie.save()
    if all([bool(shortname), bool(series)]):
        return HttpResponseRedirect(reverse("tv:episodes", args=(shortname, series)))
    return HttpResponseRedirect(request.META["HTTP_REFERER"])  # pragma: no cover - safe fallback only.


def mark_as_watched(request, shortname, series):
    """Mark the given file as watched in the database (POST target)."""
    mypath = request.POST["smb_path"]
    try:
        this_episode = Episode.objects.get(pk=mypath)
    except Episode.DoesNotExist:  # pragma: no cover
        return HttpResponseRedirect(reverse("tv:episodes", args=(shortname, series)))
    this_episode.watched = True
    this_episode.save()
    return HttpResponseRedirect(reverse("tv:episodes", args=(shortname, series)))


def manage_all_episodes(request, shortname, series):
    """Manage episode states in the database based on the action selected (POST target)."""
    this_action = request.POST["action"]
    this_series = Series.objects.get(pk=series)
    if this_action == "load_all":
        this_series.add_all_episodes()
    elif this_action == "mark_unwatched":
        this_series.episode_set.all().update(watched=False)
    elif this_action == "mark_watched":
        this_series.episode_set.all().update(watched=True)
    elif this_action == "delete_series":
        this_series.delete()
        return HttpResponseRedirect(reverse("tv:series_library", args=(shortname,)))
    return HttpResponseRedirect(reverse("tv:episodes", args=(shortname, series)))


def mark_watched_up_to(request, shortname, series):
    """Mark all episodes prior to the selected one as watched in the DB (POST target)."""
    mypath = request.POST["smb_path"]
    try:  # Confirm the episode exists
        _ = Episode.objects.get(pk=mypath)
    except Episode.DoesNotExist:  # pragma: no cover
        return HttpResponseRedirect(reverse("tv:episodes", args=(shortname, series)))
    Episode.objects.filter(series=series, smb_path__lt=mypath).update(watched=True)
    return HttpResponseRedirect(reverse("tv:episodes", args=(shortname, series)))


def kodi_control(request, shortname, series):
    """Issue commands to Kodi based on the form selection (POST target)."""
    this_action = request.POST["action"]
    k = Kodi()
    if this_action == "subs_off":
        k.subs_off()
    elif this_action == "subs_on":
        k.subs_on()
    elif this_action == "next_item":
        k.next_item()
    elif this_action == "next_stream":
        k.next_stream()
    elif this_action == "passthrough":
        # The page essentially gives you the option to toggle, so let's do that here.
        k.set_audio_passthrough(not k.get_audio_passthrough())
    return HttpResponseRedirect(reverse("tv:episodes", args=(shortname, series)))


def add_library(request):
    """Add a library to the database (POST target)."""
    this_path = request.POST["path"]
    this_prefix = request.POST["prefix"]
    this_servername = request.POST["servername"]
    this_shortname = request.POST["shortname"]
    this_content_type = request.POST["content_type"]
    this_library = Library(
        path=this_path,
        prefix=this_prefix,
        servername=this_servername,
        shortname=this_shortname,
        content_type=this_content_type,
    )
    this_library.save()
    return HttpResponseRedirect(reverse("tv:index"))


def add_series(request, shortname):
    """Add a series to the database (POST target)."""
    this_series_name = request.POST["series_name"]
    this_library = request.POST["library"]
    try:
        this_library = Library.objects.get(shortname=this_library)
    except Library.DoesNotExist:  # pragma: no cover
        return HttpResponseRedirect(reverse("tv:series_library", args=(shortname,)))
    if this_series_name == "all":
        this_library.add_all_series()
    else:
        this_library.series_set.update_or_create(series_name=this_series_name)
    return HttpResponseRedirect(reverse("tv:series_library", args=(shortname,)))


def delete_library(request):
    """Remove a library and all of its series from the database (POST target)."""
    this_library_shortname = request.POST["library"]
    try:
        this_library = Library.objects.get(shortname=this_library_shortname)
    except Library.DoesNotExist:  # pragma: no cover
        return HttpResponseRedirect(reverse("tv:index"))
    this_library.delete()
    return HttpResponseRedirect(reverse("tv:index"))


def add_player(request):
    """Configure the address of the Kodi player's JSON RPC endpoint (POST target)."""
    this_player_address = request.POST["player_address"]
    this_player = Player(pid=1, address=this_player_address)
    this_player.save()
    return HttpResponseRedirect(reverse("tv:index"))
