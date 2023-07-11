"""Class-based and function-based view backings for the URLs in the tv app."""
from functools import lru_cache
from random import choice
from string import ascii_letters, digits
from sys import maxunicode
from django.http import HttpResponseRedirect, Http404, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views import generic
from django.utils import timezone

from .models import Player, Library, Series, Episode, Movie
from .kodi import Kodi


SAFE_CHARS = "".join([ascii_letters, digits, "-", "_", ":", "."])
UNSAFE_CHARS = "".join([chr(x) for x in range(maxunicode) if chr(x) not in SAFE_CHARS])
IDTRANSLATOR = str.maketrans(SAFE_CHARS + UNSAFE_CHARS, SAFE_CHARS + "".join(["_" for x in UNSAFE_CHARS]))


@lru_cache(maxsize=None)
def get_html_id(path):
    """
    Generate an HTML-safe ID tag base on a path.

    String translation is used here because it is 86% faster on my computer than using re.sub.
    """
    return path.translate(IDTRANSLATOR)


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
    """Build a set of prototypes for a nested folder view."""
    shared_root = library.get_smb_path(library.path)
    buttons = {}
    divs = {}
    paras = {}
    for obj in object_list:
        folder, basename = obj[0].rsplit("/", 1)
        folderid = get_html_id(folder)
        paras[obj[0]] = {
            "parent": folderid,
            "displayname": basename,
            "last_watched": obj[1].strftime("%Y-%m-%d") if len(obj) > 1 and obj[1] is not None else None,
        }
        divs.setdefault(folder, {"myid": folderid})
    for folder in list(divs.keys()):
        while folder != shared_root:
            parent, basename = folder.rsplit("/", 1)
            parentid = get_html_id(parent)
            buttonid = f"button.{divs[folder]['myid']}"
            buttons.setdefault(
                folder, {"myid": buttonid, "parent": parentid, "sibling": divs[folder]["myid"], "displayname": basename}
            )
            divs[folder].update({"parent": parentid})
            divs.setdefault(parent, {"myid": parentid})
            folder = parent
    divs[shared_root].update({"parent": "flexbase"})
    return (buttons, divs, paras)


def music_json_content(request, shortname):
    """Fetch the JSON body for the music view."""
    this_library = Library.objects.get(shortname=shortname)
    this_song_list = this_library.song_set.values_list("smb_path")
    (buttons, divs, paras) = build_nested_view(this_library, this_song_list)
    return JsonResponse(
        {"buttons": buttons, "divs": divs, "paras": paras},
        json_dumps_params={"separators": (",", ":"), "sort_keys": True},
    )


def movie_json_content(request, shortname):
    """Fetch the JSON body for the movie view."""
    this_library = Library.objects.get(shortname=shortname)
    this_movie_list = this_library.movie_set.values_list("smb_path", "last_watched")
    (buttons, divs, paras) = build_nested_view(this_library, this_movie_list)
    return JsonResponse(
        {"buttons": buttons, "divs": divs, "paras": paras},
        json_dumps_params={"separators": (",", ":"), "sort_keys": True},
    )


def movie_music_view(request, shortname):
    """View the music or movie list page with custom collapsibles."""
    this_library = Library.objects.get(shortname=shortname)
    return render(
        request,
        "tv/folder_list.html",
        {"library": this_library},
    )


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
            # Lesson learned - you need localtime here because now() is always UTC by default.
            this_movie.last_watched = timezone.localtime()
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
