"""URLConf for the tv app."""
from django.urls import path

from . import views

app_name = "tv"
urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("add_library", views.add_library, name="add_library"),
    path("add_player", views.add_player, name="add_player"),
    path("delete_library", views.delete_library, name="delete_library"),
    path("kodi_control", views.kodi_control_standalone, name="kodi_control_standalone"),
    path("music/play", views.play, name="play_song"),
    path("music/<str:shortname>/json_content", views.music_json_content, name="song_library_content"),
    path("music/<str:shortname>", views.movie_music_view, name="song_library"),
    path("movies/play", views.play, name="play_movie"),
    path("movies/<str:shortname>", views.movie_music_view, name="movie_library"),
    path("movies/<str:shortname>/json_content", views.movie_json_content, name="movie_library_content"),
    path("series/<str:shortname>", views.SeriesView.as_view(), name="series_library"),
    path("series/<str:shortname>/add_series", views.add_series, name="add_series"),
    path("series/<str:shortname>/<str:series>", views.series_detail, name="episodes"),
    path("series/<str:shortname>/<str:series>/play", views.play, name="play_episode"),
    path("series/<str:shortname>/<str:series>/watched", views.mark_as_watched, name="watched_episode"),
    path(
        "series/<str:shortname>/<str:series>/manage_all_episodes", views.manage_all_episodes, name="manage_all_episodes"
    ),
    path("series/<str:shortname>/<str:series>/mark_watched_up_to", views.mark_watched_up_to, name="mark_watched_up_to"),
    path("series/<str:shortname>/<str:series>/kodi_control", views.kodi_control, name="kodi_control"),
]
