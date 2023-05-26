"""Control available admin features for the tv app."""
from django.contrib import admin

from .models import Episode, Series, Library


@admin.action(description="Mark selected episodes as watched.")
def mark_episode_set_as_watched(modeladmin, request, queryset):  # pylint: disable=W0613
    """Use the queryset.update feature to mark items watched."""
    queryset.update(watched=True)


@admin.action(description="Mark selected episodes as unwatched.")
def mark_episode_set_as_unwatched(modeladmin, request, queryset):  # pylint: disable=W0613
    """Use the queryset.update feature to mark items unwatched."""
    queryset.update(watched=False)


@admin.action(description="Mark entire series as watched.")
def mark_series_as_watched(modeladmin, request, queryset):  # pylint: disable=W0613
    """Iterate over the queryset and mark the series' episodes as watched."""
    for series in queryset:
        Episode.objects.filter(series=series).update(watched=True)


@admin.action(description="Mark entire series as unwatched.")
def mark_series_as_unwatched(modeladmin, request, queryset):  # pylint: disable=W0613
    """Iterate over the queryset and mark the series' episodes as unwatched."""
    for series in queryset:
        Episode.objects.filter(series=series).update(watched=False)


class EpisodeAdmin(admin.ModelAdmin):
    """A better view for episodes."""

    list_display = ["series", "basename", "watched"]
    list_filter = ["watched", "series"]
    search_fields = ["smb_path"]
    actions = [mark_episode_set_as_watched, mark_episode_set_as_unwatched]


class SeriesAdmin(admin.ModelAdmin):
    """A better view for series."""

    list_display = ["series_name", "library"]
    search_fields = ["series_name"]
    actions = [mark_series_as_watched, mark_series_as_unwatched]


class LibraryAdmin(admin.ModelAdmin):
    """A better view for libraries."""

    list_display = ["shortname", "path", "prefix", "servername"]
    search_fields = ["path", "shortname"]


admin.site.register(Library, LibraryAdmin)
admin.site.register(Series, SeriesAdmin)
admin.site.register(Episode, EpisodeAdmin)
