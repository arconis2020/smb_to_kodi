"""A simple command line action to sync all series from disk."""
from django.core.management.base import BaseCommand
from tv.models import Series
import logging


class Command(BaseCommand):
    """A simple command line action to sync all series from disk."""

    def handle(self, *args, **kwargs):
        """Run the add_all_episodes function that syncs files on disk to the DB."""
        logger = logging.getLogger("django")
        for series in Series.objects.all():
            logger.info(f"Updating {series.series_name} from disk.")
            series.add_all_episodes()
