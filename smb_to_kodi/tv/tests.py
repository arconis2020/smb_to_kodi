"""All unit tests for the tv app."""
from django.test import TestCase
import black
import os
import pycodestyle
import pydocstyle
import tempfile


from .models import Player, Library, Series, Episode


class StylingAndFormattingTests(TestCase):
    """Tests for the style and formatting guidelines in play for this project."""

    def test_codestyle(self):
        """Ensure compliance with PEP-8 (pycodestyle) at 120 characters."""
        style = pycodestyle.StyleGuide(max_line_length=120)
        result = style.check_files(".")
        self.assertEqual(result.total_errors, 0, "Found PEP-8 errors, see above and fix.")

    def test_black(self):
        """Ensure that all files are compliant with Black formatting expectations."""
        res = black.main(["-l", "120", "--check", "."], standalone_mode=False)
        self.assertEqual(res, 0, "Found Black reformatting requirements, run 'black -l 120 .' to fix.")

    def test_docstyle(self):
        """Ensure compliance with PEP-257 (pydocstyle)."""
        to_check = []
        for root, dirs, files in os.walk("./tv"):
            if "migrations" in root:
                continue
            for f in files:
                fullpath = os.path.join(root, f)
                if all([f.endswith(".py"), os.stat(fullpath).st_size > 0]):
                    to_check.append(fullpath)
        errors = [str(error) for error in pydocstyle.check(to_check)]
        if errors:
            raise ValueError("\n".join(errors))


class PlayerModelTests(TestCase):
    """Tests for the Player database model."""

    def test_player_replacement(self):
        """Ensure that providing the same primary key replaces the database entry instead of appending."""
        p1 = Player(pid=1, address="foo")
        p1.save()
        self.assertEqual(Player.objects.count(), 1)
        self.assertEqual(Player.objects.get(pk=1).address, "foo")
        p2 = Player(pid=1, address="bar")
        p2.save()
        self.assertEqual(Player.objects.count(), 1)
        self.assertEqual(Player.objects.get(pk=1).address, "bar")


class LibraryModelTests(TestCase):
    """Tests for the Library database model."""

    @classmethod
    def setUpClass(cls):
        """Create a temporary directory structure with known contents for testing."""
        super(LibraryModelTests, cls).setUpClass()
        cls.libdir = tempfile.TemporaryDirectory()
        cls.dirnames = []
        for x in range(10):
            this_td = tempfile.TemporaryDirectory(dir=cls.libdir.name)
            cls.dirnames.append(this_td)
        cls.testlib = Library(
            path=cls.libdir.name, prefix=tempfile.gettempdir(), servername="localhost", shortname="testlib1"
        )
        cls.testlib.save()

    def test_string_rep(self):
        """Confirm string representation of Libraries."""
        self.assertEqual(str(self.testlib), self.libdir.name)

    def test_get_smb_path(self):
        """Confirm that the smb path is predictable."""
        test_path = os.path.join(self.dirnames[0].name, "testfile")
        test_smb_path = self.testlib.get_smb_path(test_path)
        self.assertRegex(test_smb_path, "^smb://{0}".format(self.testlib.servername))
        trailer = os.path.join(os.path.basename(self.dirnames[0].name), "testfile")
        self.assertRegex(test_smb_path, "{0}$".format(trailer))

    def test_add_all_series(self):
        """Confirm that all folders are added as expected to the library."""
        self.testlib.add_all_series()
        self.assertEqual(Series.objects.filter(library=self.testlib).count(), 10)

    @classmethod
    def tearDownClass(cls):
        """Clean up the temporary directory structure."""
        super(LibraryModelTests, cls).tearDownClass()
        for x in cls.dirnames:
            x.cleanup()
        cls.libdir.cleanup()


class SeriesModelTests(TestCase):
    """Tests for the Series database model."""

    @classmethod
    def setUpClass(cls):
        """Create a temporary directory structure with known contents for testing."""
        super(SeriesModelTests, cls).setUpClass()
        cls.libdir = tempfile.TemporaryDirectory()
        cls.seriesdir = tempfile.TemporaryDirectory(dir=cls.libdir.name)
        cls.fnames = []
        for x in range(10):
            # Should be seen by mimetypes as video
            this_f = tempfile.NamedTemporaryFile(dir=cls.seriesdir.name, suffix=".mkv")
            # Should be seen by mimetypes as None
            this_nf = tempfile.NamedTemporaryFile(dir=cls.seriesdir.name)
            # Now keep these files active until the teardown.
            cls.fnames.append(this_f)
            cls.fnames.append(this_nf)
        cls.testlib = Library(
            path=cls.libdir.name, prefix=tempfile.gettempdir(), servername="localhost", shortname="testlib2"
        )
        cls.testlib.save()
        cls.testser = Series(series_name=os.path.basename(cls.seriesdir.name), library=cls.testlib)
        cls.testser.save()

    def test_string_rep(self):
        """Confirm string representation of Series."""
        self.assertEqual(str(self.testser), os.path.basename(self.seriesdir.name))

    def test_add_all_series(self):
        """Confirm that all files are added as expected to the series."""
        self.testser.add_all_episodes()
        self.assertEqual(Episode.objects.filter(series=self.testser).count(), 10)

    @classmethod
    def tearDownClass(cls):
        """Clean up the temporary directory structure."""
        super(SeriesModelTests, cls).tearDownClass()
        cls.seriesdir.cleanup()
        cls.libdir.cleanup()


class EpisodeModelTests(TestCase):
    """Tests for the Episode database model."""

    @classmethod
    def setUpClass(cls):
        """Create a temporary directory structure with known contents for testing."""
        super(EpisodeModelTests, cls).setUpClass()
        cls.libdir = tempfile.TemporaryDirectory()
        cls.seriesdir = tempfile.TemporaryDirectory(dir=cls.libdir.name)
        cls.testlib = Library(
            path=cls.libdir.name, prefix=tempfile.gettempdir(), servername="localhost", shortname="testlib3"
        )
        cls.testlib.save()
        cls.testser = Series(series_name=os.path.basename(cls.seriesdir.name), library=cls.testlib)
        cls.testser.save()
        cls.testep1 = Episode(series=cls.testser, smb_path="series/101.mkv", watched=False)
        cls.testep1.save()
        cls.testep2 = Episode(series=cls.testser, smb_path="series/102.mkv", watched=False)
        cls.testep2.save()
        cls.testep3 = Episode(series=cls.testser, smb_path="series/103.mkv", watched=False)
        cls.testep3.save()

    def test_string_rep(self):
        """Confirm string representation of Episodes."""
        self.assertEqual(str(self.testep1), "series/101.mkv")

    def test_basename(self):
        """Confirm basename functionality."""
        self.assertEqual(self.testep1.basename(), "101.mkv")

    def test_sort(self):
        """Confirm expected sorting of episodes."""
        self.assertLess(self.testep1, self.testep2)
        self.assertLess(self.testep2, self.testep3)

    @classmethod
    def tearDownClass(cls):
        """Clean up the temporary directory structure."""
        super(EpisodeModelTests, cls).tearDownClass()
        cls.seriesdir.cleanup()
        cls.libdir.cleanup()
