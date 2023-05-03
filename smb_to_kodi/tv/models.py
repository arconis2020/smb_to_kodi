"""All data model objects for the tv application."""
from django.db import models
from os import walk
from os.path import basename, join, relpath, realpath
from pathlib import Path
import mimetypes
import unicodedata


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
        for r in result:
            self.series_set.update_or_create(series_name=r)


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

    def add_all_episodes(self):
        """Find all video files in this folder, and add them as episodes for this series."""
        # First, find all of the episodes.
        found = []
        for root, dirs, files in walk(join(self.library.path, self.series_name)):
            for f in files:
                filetype = mimetypes.guess_type(f)[0]
                if filetype is None:
                    continue
                if filetype.startswith("video/"):
                    this_smb_path = self.library.get_smb_path(realpath(join(root, f)))
                    found.append(this_smb_path)
        # Now remove anything that wasn't found on disk.
        self.episode_set.exclude(smb_path__in=found).delete()
        # Now add anything that is new on disk.
        to_add = set(found) - set(self.episode_set.values_list("smb_path", flat=True))
        for ta in to_add:
            self.episode_set.create(smb_path=ta)


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
        return "{0}".format(basename(self.smb_path))
