"""URLConf for the tv app."""
from django.urls import path

from . import views

app_name = "tv"
urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("add_library", views.add_library, name="add_library"),
    path("add_player", views.add_player, name="add_player"),
    path("delete_library", views.delete_library, name="delete_library"),
    path("<str:shortname>", views.SeriesView.as_view(), name="library"),
    path("<str:shortname>/add_series", views.add_series, name="add_series"),
    path("<str:shortname>/<str:series>", views.series_detail, name="episodes"),
    path("<str:shortname>/<str:series>/play", views.play, name="play"),
    path("<str:shortname>/<str:series>/watched", views.mark_as_watched, name="watched"),
    path("<str:shortname>/<str:series>/manage_all_episodes", views.manage_all_episodes, name="manage_all_episodes"),
    path("<str:shortname>/<str:series>/mark_watched_up_to", views.mark_watched_up_to, name="mark_watched_up_to"),
    path("<str:shortname>/<str:series>/kodi_control", views.kodi_control, name="kodi_control"),
]