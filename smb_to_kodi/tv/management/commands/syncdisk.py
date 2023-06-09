"""A simple command line action to sync all series from disk."""
from django.core.management.base import BaseCommand
from tv.models import Series, Library
import logging


class Command(BaseCommand):
    """A simple command line action to sync all media from disk."""

    def handle(self, *args, **kwargs):
        """Run the add_all_episodes function that syncs files on disk to the DB."""
        logger = logging.getLogger("django")
        for series in Series.objects.all():
            logger.info(f"Updating {series.series_name} from disk.")
            series.add_all_episodes()
        for movie_lib in Library.objects.filter(content_type=Library.ContentType.MOVIES):
            logger.info(f"Updating movie library {movie_lib.shortname} from disk.")
            movie_lib.add_all_movies()
