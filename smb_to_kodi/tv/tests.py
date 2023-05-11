"""All unit tests for the tv app."""
from unittest.mock import call, patch
import os
import tempfile
import black
import pycodestyle
import pydocstyle
from django.test import TestCase
from django.urls import reverse
from requests.exceptions import ConnectionError


from .models import Player, Library, Series, Episode
from .kodi import Kodi


class DirectoryFactory:  # pylint: disable=R1732
    """A reusable object to manage directory structures required for libraries/series/episodes."""

    def __init__(self):
        """Set up the lists."""
        self.libdir = None
        self.series = []
        self.episodes = []

    def create_library(self):
        """Create a library structure."""
        self.libdir = tempfile.TemporaryDirectory()

    def create_series(self, num):
        """Create a number of series structures."""
        for _ in range(num):
            this_td = tempfile.TemporaryDirectory(dir=self.libdir.name)
            self.series.append(this_td)

    def create_episodes(self, num, dummy):
        """Create a number of basically named episodes in the first available series."""
        # Make sure that each episode has a numbered prefix in order of adding for sorting.
        # Start at 11 to support more than 10 episodes in sort order.
        prefixer = 11
        for _ in range(num):
            # Should be seen by mimetypes as video
            this_f = tempfile.NamedTemporaryFile(dir=self.series[0].name, suffix=".mkv", prefix=str(prefixer))
            self.episodes.append(this_f)
            if dummy:  # Test that mimetype filtering works
                # Should be seen by mimetypes as None
                this_nf = tempfile.NamedTemporaryFile(dir=self.series[0].name)
                self.episodes.append(this_nf)
            prefixer += 1


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
        for root, _, files in os.walk("./tv"):
            if "migrations" in root:
                continue
            for this_file in files:
                fullpath = os.path.join(root, this_file)
                if all([this_file.endswith(".py"), os.stat(fullpath).st_size > 0]):
                    to_check.append(fullpath)
        errors = [str(error) for error in pydocstyle.check(to_check)]
        if errors:
            raise ValueError("\n".join(errors))


class PlayerModelTests(TestCase):
    """Tests for the Player database model."""

    def test_player_replacement(self):
        """Ensure that providing the same primary key replaces the database entry instead of appending."""
        player_one = Player(pid=1, address="foo")
        player_one.save()
        self.assertEqual(Player.objects.count(), 1)
        self.assertEqual(Player.objects.get(pk=1).address, "foo")
        player_two = Player(pid=1, address="bar")
        player_two.save()
        self.assertEqual(Player.objects.count(), 1)
        self.assertEqual(Player.objects.get(pk=1).address, "bar")


class LibraryModelTests(TestCase):
    """Tests for the Library database model."""

    @classmethod
    def setUpClass(cls):
        """Create a temporary directory structure with known contents for testing."""
        super(LibraryModelTests, cls).setUpClass()
        cls.dfac = DirectoryFactory()
        cls.dfac.create_library()
        cls.dfac.create_series(10)
        cls.dfac.create_episodes(1, False)
        cls.testlib = Library(
            path=cls.dfac.libdir.name, prefix=tempfile.gettempdir(), servername="localhost", shortname="testlib1"
        )
        cls.testlib.save()

    def test_string_rep(self):
        """Confirm string representation of Libraries."""
        self.assertEqual(str(self.testlib), self.dfac.libdir.name)

    def test_get_smb_path(self):
        """Confirm that the smb path is predictable."""
        test_path = self.dfac.episodes[0].name
        test_smb_path = self.testlib.get_smb_path(test_path)
        self.assertRegex(test_smb_path, f"^smb://{self.testlib.servername}")
        this_dir, this_file = os.path.split(test_path)
        trailer = os.path.join(os.path.basename(this_dir), this_file)
        self.assertRegex(test_smb_path, f"{trailer}$")

    def test_add_all_series(self):
        """Confirm that all folders are added as expected to the library."""
        self.testlib.add_all_series()
        self.assertEqual(Series.objects.filter(library=self.testlib).count(), 10)


class SeriesModelTests(TestCase):
    """Tests for the Series database model."""

    @classmethod
    def setUpClass(cls):
        """Create a temporary directory structure with known contents for testing."""
        super(SeriesModelTests, cls).setUpClass()
        cls.dfac = DirectoryFactory()
        cls.dfac.create_library()
        cls.dfac.create_series(10)
        cls.dfac.create_episodes(10, True)
        cls.testlib = Library(
            path=cls.dfac.libdir.name, prefix=tempfile.gettempdir(), servername="localhost", shortname="testlib2"
        )
        cls.testlib.save()
        cls.testser = Series(series_name=os.path.basename(cls.dfac.series[0].name), library=cls.testlib)
        cls.testser.save()

    def test_string_rep(self):
        """Confirm string representation of Series."""
        self.assertEqual(str(self.testser), os.path.basename(self.dfac.series[0].name))

    def test_add_all_episodes(self):
        """Confirm that all files are added as expected to the series."""
        self.testser.add_all_episodes()
        self.assertEqual(Episode.objects.filter(series=self.testser).count(), 10)


class EpisodeModelTests(TestCase):
    """Tests for the Episode database model."""

    @classmethod
    def setUpClass(cls):
        """Create a temporary directory structure with known contents for testing."""
        super(EpisodeModelTests, cls).setUpClass()
        cls.dfac = DirectoryFactory()
        cls.dfac.create_library()
        cls.dfac.create_series(10)
        cls.dfac.create_episodes(3, False)
        cls.testlib = Library(
            path=cls.dfac.libdir.name, prefix=tempfile.gettempdir(), servername="localhost", shortname="testlib3"
        )
        cls.testlib.save()
        cls.testser = Series(series_name=os.path.basename(cls.dfac.series[0].name), library=cls.testlib)
        cls.testser.save()
        cls.testeps = []
        for episode in cls.dfac.episodes:
            this_ep = Episode(series=cls.testser, smb_path=episode.name, watched=False)
            this_ep.save()
            cls.testeps.append(this_ep)

    def test_string_rep(self):
        """Confirm string representation of Episodes."""
        self.assertEqual(str(self.testeps[0]), self.dfac.episodes[0].name)

    def test_basename(self):
        """Confirm basename functionality."""
        self.assertEqual(self.testeps[0].basename(), os.path.basename(self.dfac.episodes[0].name))

    def test_sort(self):
        """Confirm expected sorting of episodes."""
        self.assertLess(self.testeps[0], self.testeps[1])
        self.assertLess(self.testeps[1], self.testeps[2])


class TvIndexViewTests(TestCase):
    """Tests for the main Index view at /tv/."""

    def test_section_presence(self):
        """Confirm the presence of the three main sections of the index page."""
        response = self.client.get(reverse("tv:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Libraries")
        self.assertContains(response, "Add Library")
        self.assertContains(response, "Player")

    def test_player_submission_and_display(self):
        """Confirm that we can submit and then immediately see the player address."""
        post_response = self.client.post(reverse("tv:add_player"), {"player_address": "foo"})
        self.assertIn(post_response.status_code, [200, 302])
        get_response = self.client.get(reverse("tv:index"))
        self.assertIn(get_response.status_code, [200, 302])
        self.assertContains(get_response, 'value="foo"')

    def test_library_submission_and_display(self):
        """Confirm that we can submit and then immediately see a library."""
        post_response = self.client.post(
            reverse("tv:add_library"),
            {"path": "/mnt/video/Series", "prefix": "/mnt", "servername": "samba.local", "shortname": "video"},
        )
        self.assertIn(post_response.status_code, [200, 302])
        get_response = self.client.get(reverse("tv:index"))
        self.assertIn(get_response.status_code, [200, 302])
        self.assertContains(get_response, "/mnt/video/Series")


class TvSeriesViewTests(TestCase):
    """Tests for the Series view of a particular library."""

    @classmethod
    def setUpClass(cls):
        """Create a temporary directory structure with known contents for testing."""
        super(TvSeriesViewTests, cls).setUpClass()
        cls.dfac = DirectoryFactory()
        cls.dfac.create_library()
        cls.dfac.create_series(3)
        cls.testlib = Library(
            path=cls.dfac.libdir.name, prefix=tempfile.gettempdir(), servername="localhost", shortname="testlib4"
        )
        cls.testlib.save()

    def test_section_presence_and_form_functions(self):
        """Confirm the presence of the four main sections of the series page, and confirm form outputs."""
        # This has to be one test because things MUST run in order.
        # Step 1: Check the page structure.
        response = self.client.get(reverse("tv:library", args=("testlib4",)))
        self.assertIn(response.status_code, [200, 302])
        self.assertContains(response, "Active Series List")
        self.assertContains(response, "Available Series List")
        self.assertContains(response, "Add Series")
        self.assertContains(response, "Delete Library")
        # Step 2: Test that you can add a series.
        test_series_name = os.path.basename(self.dfac.series[0].name)
        response = self.client.post(
            reverse("tv:add_series", args=("testlib4",)), {"series_name": test_series_name, "library": "testlib4"}
        )
        self.assertIn(response.status_code, [200, 302])
        response = self.client.get(reverse("tv:library", args=("testlib4",)))
        self.assertContains(response, test_series_name)
        # Step 3: Test the add all feature.
        response = self.client.post(
            reverse("tv:add_series", args=("testlib4",)), {"series_name": "all", "library": "testlib4"}
        )
        self.assertIn(response.status_code, [200, 302])
        self.assertEqual(Series.objects.filter(library=self.testlib).count(), 3)
        # Step 4: Test that you can delete a library.
        response = self.client.post(reverse("tv:delete_library"), {"library": "testlib4"})
        self.assertIn(response.status_code, [200, 302])
        response = self.client.get(reverse("tv:index"))
        self.assertIn(response.status_code, [200, 302])
        self.assertContains(response, "No libraries are available.")
        response = self.client.get(reverse("tv:library", args=("testlib4",)))
        self.assertEqual(response.status_code, 404)


class TvSeriesDetailViewTests(TestCase):
    """Tests for the Series detail view that allows playing episodes."""

    @classmethod
    def setUpClass(cls):
        """Create a temporary directory structure with known contents for testing."""
        super(TvSeriesDetailViewTests, cls).setUpClass()
        cls.dfac = DirectoryFactory()
        cls.dfac.create_library()
        cls.dfac.create_series(1)
        cls.dfac.create_episodes(3, False)
        cls.testlib = Library(
            path=cls.dfac.libdir.name, prefix=tempfile.gettempdir(), servername="localhost", shortname="testlib5"
        )
        cls.testlib.save()
        cls.testser = Series(series_name=os.path.basename(cls.dfac.series[0].name), library=cls.testlib)
        cls.testser.save()

    @patch("tv.views.Kodi")
    def test_full_page_behavior(self, mock_kodi):
        """Exercise all parts of the series detail page."""
        # Must be a single test to avoid race conditions with data.
        # Step 1: Test the presence of various elements.
        response = self.client.get(reverse("tv:episodes", args=("testlib5", self.testser.series_name)))
        self.assertIn(response.status_code, [200, 302])
        for chkstr in ["Next Episode", "Random Episode", "Selected Episode", "All Episodes", "Kodi Control"]:
            self.assertContains(response, chkstr)
        # Step 3a: Submit the form action to load the episodes.
        response = self.client.post(
            reverse("tv:manage_all_episodes", args=("testlib5", self.testser.series_name)), {"action": "load_all"}
        )
        self.assertIn(response.status_code, [200, 302])
        # Step 3b: Refetch the detail page and check for episode names.
        response = self.client.get(reverse("tv:episodes", args=("testlib5", self.testser.series_name)))
        self.assertIn(response.status_code, [200, 302])
        self.assertContains(response, self.dfac.episodes[0].name)
        # Set up some important variables for later.
        ep_smb_paths = list(
            Episode.objects.filter(series=self.testser.series_name)
            .order_by("smb_path")
            .values_list("smb_path", flat=True)
        )
        first_ep_smb_path, second_ep_smb_path, last_ep_smb_path = ep_smb_paths
        # Step 4a: Mark up to the very last episode as watched.
        response = self.client.post(
            reverse("tv:mark_watched_up_to", args=("testlib5", self.testser.series_name)),
            {"smb_path": last_ep_smb_path},
        )
        self.assertIn(response.status_code, [200, 302])
        # Step 4b: Refetch the detail page and check that the next episode is the last one.
        expected = f'name="smb_path" id="next" value="{last_ep_smb_path}"'
        response = self.client.get(reverse("tv:episodes", args=("testlib5", self.testser.series_name)))
        self.assertIn(response.status_code, [200, 302])
        self.assertContains(response, expected)
        # Step 5a: Mark all episodes as unwatched.
        response = self.client.post(
            reverse("tv:manage_all_episodes", args=("testlib5", self.testser.series_name)), {"action": "mark_unwatched"}
        )
        self.assertIn(response.status_code, [200, 302])
        # Step 5b: Refetch the detail page and check that the next episode is the first one.
        expected = f'name="smb_path" id="next" value="{first_ep_smb_path}"'
        response = self.client.get(reverse("tv:episodes", args=("testlib5", self.testser.series_name)))
        self.assertIn(response.status_code, [200, 302])
        self.assertContains(response, expected)
        # Step 6a: Mark the first episode as watched.
        response = self.client.post(
            reverse("tv:watched", args=("testlib5", self.testser.series_name)),
            {"smb_path": first_ep_smb_path},
        )
        self.assertIn(response.status_code, [200, 302])
        # Step 6b: Refetch the detail page and check that the next episode is the second one.
        expected = f'name="smb_path" id="next" value="{second_ep_smb_path}"'
        response = self.client.get(reverse("tv:episodes", args=("testlib5", self.testser.series_name)))
        self.assertIn(response.status_code, [200, 302])
        self.assertContains(response, expected)
        # Step 7a: Test the play button and advancing episodes.
        mock_kodi.confirm_successful_play.return_value = True
        response = self.client.post(
            reverse("tv:play", args=("testlib5", self.testser.series_name)),
            {"smb_path": second_ep_smb_path},
        )
        # Confirm that Kodi is being called.
        expected_call_list = [
            call().add_and_play(second_ep_smb_path),
            call().confirm_successful_play(second_ep_smb_path),
        ]
        for e_c in expected_call_list:
            self.assertIn(e_c, mock_kodi.mock_calls)
        self.assertIn(response.status_code, [200, 302])
        # Step 7b: Refetch the detail page and check that the next episode is the last one.
        expected = f'name="smb_path" id="next" value="{last_ep_smb_path}"'
        response = self.client.get(reverse("tv:episodes", args=("testlib5", self.testser.series_name)))
        self.assertIn(response.status_code, [200, 302])
        self.assertContains(response, expected)
        # Step 8a: Exercise the available Kodi controls.
        action_list = [
            ("subs_off", call().subs_off()),
            ("subs_on", call().subs_on()),
            ("next_item", call().next_item()),
            ("next_stream", call().next_stream()),
        ]
        for action in action_list:
            expected_call = action[1]
            response = self.client.post(
                reverse("tv:kodi_control", args=("testlib5", self.testser.series_name)), {"action": action[0]}
            )
            self.assertIn(response.status_code, [200, 302])
            self.assertIn(expected_call, mock_kodi.mock_calls)
        # Step 8b: Refetch the detail page and confirm that nothing has advanced (same as 7b).
        expected = f'name="smb_path" id="next" value="{last_ep_smb_path}"'
        response = self.client.get(reverse("tv:episodes", args=("testlib5", self.testser.series_name)))
        self.assertIn(response.status_code, [200, 302])
        self.assertContains(response, expected)
        # Step 9: Test series deletion.
        response = self.client.post(
            reverse("tv:manage_all_episodes", args=("testlib5", self.testser.series_name)), {"action": "delete_series"}
        )
        self.assertIn(response.status_code, [200, 302])
        self.assertEqual(Series.objects.filter(series_name=self.testser.series_name).count(), 0)


@patch("tv.kodi.requests.post")
class KodiTests(TestCase):
    """Test that the Kodi library works as intended."""

    @classmethod
    def setUpClass(cls):
        """Create a single Kodi instance for testing."""
        super(KodiTests, cls).setUpClass()
        cls.player = Player(pid=1, address="foo")
        cls.player.save()
        cls.kodi = Kodi()
        cls.nothing_playing = {
            "id": "1",
            "jsonrpc": "2.0",
            "result": {"item": {"file": "", "label": "", "type": "unknown"}},
        }
        cls.foo_playing = {
            "id": "1",
            "jsonrpc": "2.0",
            "result": {"item": {"file": "foo", "label": "foo", "type": "unknown"}},
        }
        cls.foo_in_playlist = {
            "id": "1",
            "jsonrpc": "2.0",
            "result": {
                "items": [{"file": "foo", "label": "foo", "type": "unknown"}],
                "limits": {"end": 1, "start": 0, "total": 1},
            },
        }
        cls.generic_ok = {"id": "1", "jsonrpc": "2.0", "result": "OK"}

    def test_now_playing(self, mock_post):
        """Test that the now_playing function returns our expected True/False tuples."""
        # Step 1: Test that nothing playing returns the False tuple.
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = self.nothing_playing
        result = self.kodi.now_playing()
        self.assertEqual(result, (False, "None"))
        # Step 2: Test that a bad connection returns the False tuple.
        mock_post.reset_mock(return_value=True, side_effect=True)
        mock_post.side_effect = ConnectionError("Not Connected.")
        result = self.kodi.now_playing()
        self.assertEqual(result, (False, "None"))
        # Step 3: Test that something playing returns the True tuple.
        mock_post.reset_mock(return_value=True, side_effect=True)
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = self.foo_playing
        result = self.kodi.now_playing()
        self.assertEqual(result, (True, "foo"))

    @patch("tv.kodi.Kodi.now_playing", return_value=(True, "foo"))
    def test_confirm_successful_play(self, mock_play, mock_post):  # pylint: disable=W0613
        """Test that the confirm_successful_play function returns True/False based on playlist and connection."""
        # Step 1: Test that we get True when the file is in the playlist.
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = self.foo_in_playlist
        self.assertTrue(self.kodi.confirm_successful_play("foo"))
        # Step 2: Test that we get False when the file is NOT in the playlist.
        self.assertFalse(self.kodi.confirm_successful_play("bar"))
        # Step 3: Test that we get False when there is no connection to Kodi.
        mock_post.reset_mock(return_value=True, side_effect=True)
        mock_post.side_effect = ConnectionError("Not Connected.")
        self.assertFalse(self.kodi.confirm_successful_play("foo"))

    def log_with_connection(self, mock_post, kodi_function, kodi_function_args, exp_log_output):
        """Run a Kodi function and confirm the log output, following DRY."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = self.generic_ok
        with self.assertLogs("django", level="INFO") as lm1:
            kodi_function(*kodi_function_args)
        self.assertEqual(lm1.output, exp_log_output)

    def log_without_connection(self, mock_post, kodi_function, kodi_function_args, exp_log_output):
        """Run a Kodi function and confirm the log output, following DRY."""
        mock_post.reset_mock(return_value=True, side_effect=True)
        mock_post.side_effect = ConnectionError("Not Connected.")
        with self.assertLogs("django", level="INFO") as lm1:
            kodi_function(*kodi_function_args)
        self.assertEqual(lm1.output, exp_log_output)

    def test_add_to_playlist(self, mock_post):
        """Test that the add_to_playlist function logs as expected."""
        # Step 1: Test that we get the good log entry when connected.
        self.log_with_connection(
            mock_post, self.kodi.add_to_playlist, ("foo",), ["INFO:django:Added foo to playlist successfully!"]
        )
        # Step 2: Test that we get the bad log entry when not connected.
        self.log_without_connection(
            mock_post,
            self.kodi.add_to_playlist,
            ("foo",),
            ["ERROR:django:PROBLEM: foo not added to playlist. Try a different way."],
        )

    def test_clear_playlist(self, mock_post):
        """Test that the clear_playlist function logs as expected."""
        # Step 1: Test that we get the good log entry when connected.
        self.log_with_connection(mock_post, self.kodi.clear_playlist, (), ["INFO:django:Clearing playlist: OK"])
        # Step 2: Test that we get the bad log entry when not connected.
        self.log_without_connection(
            mock_post, self.kodi.clear_playlist, (), ["INFO:django:Clearing playlist: {'connection': False}"]
        )

    def test_play_it(self, mock_post):
        """Test that the play_it function logs as expected."""
        # Step 1: Test that we get the good log entry when connected.
        self.log_with_connection(mock_post, self.kodi.play_it, (), ["INFO:django:Playing: OK"])
        # Step 2: Test that we get the bad log entry when not connected.
        self.log_without_connection(mock_post, self.kodi.play_it, (), ["INFO:django:Playing: {'connection': False}"])

    def test_next_item(self, mock_post):
        """Test that the next_item function logs as expected."""
        # Step 1: Test that we get the good log entry when connected.
        self.log_with_connection(mock_post, self.kodi.next_item, (), ["INFO:django:Skipping to next item: OK"])
        # Step 2: Test that we get the bad log entry when not connected.
        self.log_without_connection(
            mock_post, self.kodi.next_item, (), ["INFO:django:Skipping to next item: {'connection': False}"]
        )

    def test_next_stream(self, mock_post):
        """Test that the next_stream function logs as expected."""
        # Step 1: Test that we get the good log entry when connected.
        self.log_with_connection(mock_post, self.kodi.next_stream, (), ["INFO:django:Skipping to next stream: OK"])
        # Step 2: Test that we get the bad log entry when not connected.
        self.log_without_connection(
            mock_post, self.kodi.next_stream, (), ["INFO:django:Skipping to next stream: {'connection': False}"]
        )

    def test_subs_off(self, mock_post):
        """Test that the subs_off function logs as expected."""
        # Step 1: Test that we get the good log entry when connected.
        self.log_with_connection(mock_post, self.kodi.subs_off, (), ["INFO:django:Dropping subtitles: OK"])
        # Step 2: Test that we get the bad log entry when not connected.
        self.log_without_connection(
            mock_post, self.kodi.subs_off, (), ["INFO:django:Dropping subtitles: {'connection': False}"]
        )

    def test_subs_on(self, mock_post):
        """Test that the subs_on function logs as expected."""
        # Step 1: Test that we get the good log entry when connected.
        self.log_with_connection(mock_post, self.kodi.subs_on, (), ["INFO:django:Enabling subtitles: OK"])
        # Step 2: Test that we get the bad log entry when not connected.
        self.log_without_connection(
            mock_post, self.kodi.subs_on, (), ["INFO:django:Enabling subtitles: {'connection': False}"]
        )

    def test_set_audio_passthrough(self, mock_post):
        """Test that the set_audio_passthrough function logs as expected."""
        # Step 1: Test that we get the good log entry when connected.
        self.log_with_connection(
            mock_post, self.kodi.set_audio_passthrough, (True,), ["INFO:django:Enabling passthrough: OK"]
        )
        # Step 2: Test that we get the good log entry when connected and trying to disable passthrough
        self.log_with_connection(
            mock_post, self.kodi.set_audio_passthrough, (False,), ["INFO:django:Disabling passthrough: OK"]
        )
        # Step 3: Test that we get the bad log entry when not connected.
        self.log_without_connection(
            mock_post,
            self.kodi.set_audio_passthrough,
            (True,),
            ["INFO:django:Enabling passthrough: {'connection': False}"],
        )