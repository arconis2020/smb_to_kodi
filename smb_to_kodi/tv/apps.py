"""AppConfig for the tv app."""
from django.apps import AppConfig


class TvConfig(AppConfig):
    """Master class for tv AppConfig."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "tv"
