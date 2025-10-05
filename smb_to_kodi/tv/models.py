"""All data model objects for the tv application."""
from os import scandir
from os.path import basename, join, relpath
from pathlib import Path
import mimetypes
import unicodedata
from django.contrib import admin
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

    class ContentType(models.IntegerChoices):
        """Set simple constants for the types of media we support."""

        SERIES = 0
        MOVIES = 1
        MUSIC = 2

    path = models.CharField(primary_key=True)
    prefix = models.CharField(max_length=255)
    servername = models.CharField(max_length=255)
    shortname = models.CharField(max_length=255, unique=True, default="video")
    content_type = models.IntegerField(choices=ContentType.choices, default=ContentType.SERIES)

    def save(self, *args, **kwargs):
        """Override save to automatically add all series when creating a new library, because it's quick."""
        super().save(*args, **kwargs)
        ctype = int(self.content_type)  # This comes through the form as a string and is coerced elsewhere.
        if ctype == self.ContentType.SERIES:
            self.add_all_series()
        elif ctype == self.ContentType.MOVIES:
            self.add_all_movies()
        elif ctype == self.ContentType.MUSIC:
            self.add_all_songs()

    def __str__(self):
        """Return an easy string representation."""
        return self.path

    def get_smb_path(self, path):
        """Use the servername and prefix attributes to calculate the correct SAMBA path for a given file."""
        rel_path = relpath(path, self.prefix)
        # Normalize unicode filenames
        rel_path = unicodedata.normalize("NFC", rel_path)
        return join("smb://", self.servername, rel_path)

    def scan_for_media(self, starting_path, mimetype_prefix):  # pylint: disable=R1710
        """Generate filenames recursively through paths."""
        # This custom method is 20% faster than os.walk, and 47% faster than Path.rglob.
        try:
            dirs = scandir(starting_path)
        except FileNotFoundError:
            return []
        for direntry in dirs:
            if "@eaDir" in direntry.path or "#recycle" in direntry.path:  # pragma: no cover
                continue
            if direntry.is_dir(follow_symlinks=False):
                yield from self.scan_for_media(direntry.path, mimetype_prefix)
            elif direntry.is_file(follow_symlinks=False):
                filetype = mimetypes.guess_type(direntry.path)[0]
                if filetype is None:
                    continue
                if filetype.startswith(mimetype_prefix):
                    yield self.get_smb_path(direntry.path)

    def add_all_songs(self):
        """Find all song files in this folder structrue, and add them as songs for this library."""
        # First, find all of the songs.
        found = list(self.scan_for_media(self.path, "audio/"))
        # Now remove anything that wasn't found on disk.
        self.song_set.exclude(smb_path__in=found).delete()
        # Now add anything that is new on disk.
        to_add = set(found) - set(self.song_set.values_list("smb_path", flat=True))
        to_add = [Song(library=self, smb_path=x) for x in to_add]
        self.song_set.bulk_create(to_add)

    def add_all_movies(self):
        """Find all video files in this folder structrue, and add them as movies for this library."""
        # First, find all of the Movies.
        found = list(self.scan_for_media(self.path, "video/"))
        # Now get the basenames of everything in the library for watch marking.
        current = {x.basename(): x.last_watched for x in self.movie_set.filter(last_watched__isnull=False)}
        # Now remove anything that wasn't found on disk.
        self.movie_set.exclude(smb_path__in=found).delete()
        # Now add anything that is new on disk.
        to_add = set(found) - set(self.movie_set.values_list("smb_path", flat=True))
        to_add = [Movie(library=self, smb_path=x, last_watched=current.get(basename(x), None)) for x in to_add]
        self.movie_set.bulk_create(to_add)

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
        ordering = ["series_name"]

    series_name = models.CharField(max_length=255, primary_key=True)
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
        seriesdir = join(self.library.path, self.series_name)
        found = list(self.library.scan_for_media(seriesdir, "video/"))
        # Now remove anything that wasn't found on disk.
        self.episode_set.exclude(smb_path__in=found).delete()
        # Now add anything that is new on disk.
        to_add = set(found) - set(self.episode_set.values_list("smb_path", flat=True))
        to_add = [Episode(series=self, smb_path=x) for x in to_add]
        self.episode_set.bulk_create(to_add)

    @property
    def comp_pct(self):
        """Calculate the completion percentage of the series based on watched episodes."""
        # Use one query, and no objectification, to speed up processing.
        watches = list(self.episode_set.values_list("watched", flat=True))
        return round(100 * watches.count(True) / len(watches), None)


class SMBFile(models.Model):
    """A base class to provide simple attributes and interfaces needed by all media file types."""

    smb_path = models.CharField(max_length=512, primary_key=True)

    class Meta:
        """Control the ordering in the admin site."""

        abstract = True
        ordering = ["smb_path"]

    def __str__(self):
        """Return an easy string representation."""
        return self.smb_path

    def __lt__(self, other):
        """Enable easy sorting using database functions like order_by."""
        return self.smb_path < other.smb_path

    @admin.display(ordering="smb_path")
    def basename(self):
        """Return a shortname for the episode for easy display purposes."""
        my_basename = basename(self.smb_path)
        return f"{my_basename}"


class Episode(SMBFile):
    """A representation of a single episode of a series."""

    series = models.ForeignKey(Series, on_delete=models.CASCADE)
    watched = models.BooleanField(default=False)


class Movie(SMBFile):
    """A representation of a single Movie."""

    library = models.ForeignKey(Library, on_delete=models.CASCADE)
    last_watched = models.DateTimeField("Date last watched", blank=True, null=True)


class Song(SMBFile):
    """A representation of a single Song."""

    library = models.ForeignKey(Library, on_delete=models.CASCADE)
