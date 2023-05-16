"""All data model objects for the tv application."""
from os.path import basename, join, relpath
from pathlib import Path
import mimetypes
import unicodedata
from django.db import models
from django.db.models import Count


class Player(models.Model):
    """A model to store the player address in the database for easy config."""

    pid = models.IntegerField(primary_key=True)
    address = models.CharField(max_length=255)


class Library(models.Model):
    """A representation of a media library which contains many series."""

    class Meta:
        """Control the naming in the admin site."""

        verbose_name_plural = "libraries"

    path = models.CharField(max_length=255, primary_key=True)
    prefix = models.CharField(max_length=255)
    servername = models.CharField(max_length=255)
    shortname = models.CharField(max_length=255, unique=True, default="video")

    def __str__(self):
        """Return an easy string representation."""
        return self.path

    def get_smb_path(self, path):
        """Use the servername and prefix attributes to calculate the correct SAMBA path for a given file."""
        rel_path = relpath(path, self.prefix)
        # Normalize unicode filenames
        rel_path = unicodedata.normalize("NFC", rel_path)
        return join("smb://", self.servername, rel_path)

    def add_all_series(self):
        """Find all subdirectories in this library, and treat them as Series objects, loading them in."""
        listing = Path(self.path)
        result = [x.name for x in listing.iterdir() if x.is_dir()]
        # Add the new series, don't touch anything that exists.
        to_add = set(result) - set(self.series_set.values_list("series_name", flat=True))
        to_add = [Series(library=self, series_name=x) for x in to_add]
        self.series_set.bulk_create(to_add)

    def get_series_by_state(self):
        """Return a 3-tuple of sets where the series listed are active, new, and completed."""
        # Doing this at the library level yields a 90% speed improvement over marking each series.
        # Using sets instead of QuerySets allows multi-set math and rapid resolution.
        empty = self.series_set.annotate(c=Count("episode")).filter(c__lt=1).distinct()  # Empty series are also new.
        unwatched = self.series_set.filter(episode__watched=False).distinct()
        watched = self.series_set.filter(episode__watched=True).distinct()
        active = sorted(set(unwatched) & set(watched))
        new = sorted((set(empty) | set(unwatched)) - set(watched))
        completed = sorted(set(watched) - set(unwatched))
        return (active, new, completed)


class Series(models.Model):
    """A representation of a single series in a media library that contains many episodes."""

    class Meta:
        """Control the naming in the admin site."""

        verbose_name_plural = "series"

    series_name = models.CharField(max_length=80, primary_key=True)
    library = models.ForeignKey(Library, on_delete=models.CASCADE)

    def __str__(self):
        """Return an easy string representation."""
        return self.series_name

    def __lt__(self, other):
        """Enable easy sorting using database functions like order_by."""
        return self.series_name < other.series_name

    def add_all_episodes(self):
        """Find all video files in this folder, and add them as episodes for this series."""
        # First, find all of the episodes.
        found = []
        seriesdir = join(self.library.path, self.series_name)
        for path in Path(seriesdir).rglob("*"):
            if "@eaDir" in str(path):  # pragma: no cover
                continue
            filetype = mimetypes.guess_type(path)[0]
            if filetype is None:
                continue
            if filetype.startswith("video/"):
                found.append(str(path))
        # Now remove anything that wasn't found on disk.
        found = [self.library.get_smb_path(x) for x in found]
        self.episode_set.exclude(smb_path__in=found).delete()
        # Now add anything that is new on disk.
        to_add = set(found) - set(self.episode_set.values_list("smb_path", flat=True))
        to_add = [Episode(series=self, smb_path=x) for x in to_add]
        self.episode_set.bulk_create(to_add)


class Episode(models.Model):
    """A representation of a single episode of a series."""

    series = models.ForeignKey(Series, on_delete=models.CASCADE)
    smb_path = models.CharField(max_length=200, primary_key=True)
    watched = models.BooleanField(default=False)

    def __str__(self):
        """Return an easy string representation."""
        return self.smb_path

    def __lt__(self, other):
        """Enable easy sorting using database functions like order_by."""
        return self.smb_path < other.smb_path

    def basename(self):
        """Return a shortname for the episode for easy display purposes."""
        my_basename = basename(self.smb_path)
        return f"{my_basename}"
