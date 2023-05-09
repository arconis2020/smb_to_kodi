"""Class-based and function-based view backings for the URLs in the tv app."""
from django.db.models import Count
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_list_or_404, get_object_or_404, render
from django.urls import reverse
from django.views import generic
from random import choice

from .models import Player, Library, Series, Episode
from .kodi import Kodi


class IndexView(generic.ListView):
    """Main index view for the /tv/ route."""

    template_name = "tv/index.html"

    def get_context_data(self, **kwargs):
        """Add page context items for better rendering."""
        context = super().get_context_data(**kwargs)
        context["current_player"] = Player.objects.get(pk=1).address if Player.objects.count() == 1 else ""
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
        context["active_series_list"] = (
            Series.objects.filter(library__shortname=self.kwargs["shortname"])
            .annotate(c=Count("episode"))
            .filter(c__gt=0)
        )
        context["available_series_list"] = (
            Series.objects.filter(library__shortname=self.kwargs["shortname"])
            .annotate(c=Count("episode"))
            .filter(c__lt=1)
        )
        context["current_player"] = Player.objects.get(pk=1).address if Player.objects.count() == 1 else ""
        return context

    def get_queryset(self):
        """Return the list of current series in this library in sorted order."""
        this_sn = self.kwargs["shortname"]
        libcheck = Library.objects.filter(shortname=this_sn).count()
        if libcheck > 0:
            return Series.objects.filter(library__shortname=this_sn).order_by("series_name")
        else:
            raise Http404("No library of that name is loaded in the DB.")


def series_detail(request, shortname, series):
    """View the episode control page for a single series."""
    this_series = Episode.objects.filter(series=series).order_by("smb_path")
    unwatched = this_series.filter(watched=False).order_by("smb_path")
    next_episode = unwatched[0] if bool(unwatched) else "No episodes loaded"
    random_episode = choice(unwatched) if bool(unwatched) else "No episodes loaded"
    return render(
        request,
        "tv/series_detail.html",
        {
            "next_episode": next_episode,
            "random_episode": random_episode,
            "series_name": series,
            "shortname": shortname,
            "eplist": this_series,
        },
    )


def play(request, shortname, series):
    """Play the given file in Kodi (POST target)."""
    mypath = request.POST["smb_path"]
    k = Kodi()
    k.addAndPlay(mypath)
    if k.confirmSuccessfulPlay(mypath):
        this_episode = Episode.objects.get(pk=mypath)
        this_episode.watched = True
        this_episode.save()
    return HttpResponseRedirect(reverse("tv:episodes", args=(shortname, series)))


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
    elif this_action == "delete_series":
        this_series.delete()
        return HttpResponseRedirect(reverse("tv:library", args=(shortname,)))
    return HttpResponseRedirect(reverse("tv:episodes", args=(shortname, series)))


def mark_watched_up_to(request, shortname, series):
    """Mark all episodes prior to the selected one as watched in the DB (POST target)."""
    mypath = request.POST["smb_path"]
    try:
        this_episode = Episode.objects.get(pk=mypath)
    except Episode.DoesNotExist:  # pragma: no cover
        return HttpResponseRedirect(reverse("tv:episodes", args=(shortname, series)))
    Episode.objects.filter(series=series, smb_path__lt=mypath).update(watched=True)
    return HttpResponseRedirect(reverse("tv:episodes", args=(shortname, series)))


def kodi_control(request, shortname, series):
    """Issue commands to Kodi based on the form selection (POST target)."""
    this_action = request.POST["action"]
    k = Kodi()
    if this_action == "subsOff":
        k.subsOff()
    elif this_action == "subsOn":
        k.subsOn()
    elif this_action == "nextItem":
        k.nextItem()
    elif this_action == "nextStream":
        k.nextStream()
    return HttpResponseRedirect(reverse("tv:episodes", args=(shortname, series)))


def add_library(request):
    """Add a library to the database (POST target)."""
    this_path = request.POST["path"]
    this_prefix = request.POST["prefix"]
    this_servername = request.POST["servername"]
    this_shortname = request.POST["shortname"]
    this_library = Library(path=this_path, prefix=this_prefix, servername=this_servername, shortname=this_shortname)
    this_library.save()
    return HttpResponseRedirect(reverse("tv:index"))


def add_series(request, shortname):
    """Add a series to the database (POST target)."""
    this_series_name = request.POST["series_name"]
    this_library = request.POST["library"]
    try:
        this_library = Library.objects.get(shortname=this_library)
    except Library.DoesNotExist:  # pragma: no cover
        return HttpResponseRedirect(reverse("tv:library", args=(shortname,)))
    if this_series_name == "all":
        this_library.add_all_series()
    else:
        this_library.series_set.update_or_create(series_name=this_series_name)
    return HttpResponseRedirect(reverse("tv:library", args=(shortname,)))


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
    p = Player(pid=1, address=this_player_address)
    p.save()
    return HttpResponseRedirect(reverse("tv:index"))
