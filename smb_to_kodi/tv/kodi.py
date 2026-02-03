"""A module to control a Kodi/XMBC media player over the network using JSONRPC."""
from time import sleep
import logging
import mimetypes
import requests
from .models import Player


class Kodi:
    """Represent the player as a single object so that functions are easy to call."""

    def __init__(self):
        """Set up the basic reusable attributes and logging."""
        self.url = Player.objects.get(pk=1).address
        self.struct = {"jsonrpc": "2.0", "id": "1", "method": "Player.Open", "params": {}}
        self.headers = {"Content-Type": "application/json"}
        self.logger = logging.getLogger("django")

    def _runit(self, specific_params):
        """Connect to Kodi and send the command, then return the result to the caller."""
        paramdict = self.struct.copy()
        paramdict.update(specific_params)
        try:
            res = requests.post(url=self.url, json=paramdict, headers=self.headers, timeout=3)
            return res.json()
        except requests.exceptions.RequestException:
            return {"result": {"connection": False}}

    def _select_ids(self, filename):
        """Select the playlist and player IDs based on the mimetype of the filename."""
        filetype = mimetypes.guess_type(filename)[0]
        if filetype.startswith("video"):
            # Video player ID and playlist ID are both 1.
            return (1, 1)
        if filetype.startswith("audio"):
            # Video player ID and playlist ID are both 0.
            return (0, 0)
        return (None, None)  # pragma: no cover - safety catch for pylint.

    def get_active_player(self):
        """
        Get the active audio/video player ID.

        THIS FUNCTION IS UNRELIABLE DURING STATE CHANGE.

        This function will always return the list of active players if there is a FULLY active player.
        In the event that a player is transitioning between inactive and active, such as immediately
        after a Player.Open event, this function will return None even while Player.GetItem will show
        that there is an active item. This is a problem internal to the Kodi API, and can't be fixed
        in this codebase. A workaround for this can be to loop this function, possibly w/a timeout.
        """
        # 0 for audio, 1 for video, 2 for pictures (not supported)
        specific_params = {"method": "Player.GetActivePlayers"}
        res = self._runit(specific_params)
        if isinstance(res["result"], list):
            # Got a list of active players.
            active_players = [x["playerid"] for x in res["result"]]
            return active_players[0] if len(active_players) > 0 else None
        # In the specific event that Kodi is unreachable, return False to let the caller know.
        if res["result"] == {"connection": False}:
            return False
        return None  # This is for when Kodi IS reachable but there are no active players.

    def now_playing(self):
        """Obtain the name of the currently playing item, if any, and confirm the player is playing."""
        # First get the active players so we support both audio and video.
        playerid = self.get_active_player()
        if playerid is None:
            # If there are no active players, then we're not playing.
            return (False, "None")
        specific_params = {"method": "Player.GetItem", "params": {"playerid": playerid, "properties": ["file"]}}
        res = self._runit(specific_params)
        try:
            playing_file = res["result"]["item"]["file"]
            assert bool(playing_file)
            return (True, playing_file)
        except (KeyError, AssertionError):  # pragma: no cover - safety case leftover from before get_active_player
            return (False, "None")

    def confirm_successful_play(self, filename):
        """Confirm that the filename is in the current playlist, and that the player is playing."""
        playlistid, _ = self._select_ids(filename)
        specific_params = {"method": "Playlist.GetItems", "params": {"playlistid": playlistid, "properties": ["file"]}}
        res = self._runit(specific_params)
        try:
            files = [x["file"] for x in res["result"]["items"]]
            assert filename in files
        except (KeyError, AssertionError):
            return False
        return self.now_playing()[0]

    def add_to_playlist(self, filename):
        """Add the filename (str) to the current playlist."""
        playlistid, _ = self._select_ids(filename)
        specific_params = {"method": "Playlist.Add", "params": {"playlistid": playlistid, "item": {"file": filename}}}
        res = self._runit(specific_params)
        out = res.get("result")
        if out and out == "OK":
            self.logger.info(f"Added {filename} to playlist successfully!")
        else:
            self.logger.error(f"PROBLEM: {filename} not added to playlist. Try a different way.")

    def clear_playlists(self):
        """Clear the current audio/video playlists."""
        for playlistid in [0, 1]:
            specific_params = {"method": "Playlist.Clear", "params": {"playlistid": playlistid}}
            res = self._runit(specific_params)
            self.logger.info(f"Clearing playlist: {res.get('result')}")

    def play_it(self, filename):
        """Press the play button, likely playing the first item in the current playlist."""
        # Use the filename as a convenient shortcut to select the playlist ID.
        playlistid, _ = self._select_ids(filename)
        specific_params = {"method": "Player.Open", "params": {"item": {"playlistid": playlistid}}}
        res = self._runit(specific_params)
        self.logger.info(f"Playing: {res.get('result')}")
        if playlistid == 0:
            # If we're playing audio, set the window to visualization.
            specific_params = {"method": "GUI.ActivateWindow", "params": {"window": "visualisation"}}
            res = self._runit(specific_params)
            self.logger.info(f"Showing visualization: {res.get('result')}")

    def next_item(self):
        """Advance to the next item in the current playlist."""
        playerid = self.get_active_player()
        specific_params = {"method": "Player.GoTo", "params": {"playerid": playerid, "to": "next"}}
        res = self._runit(specific_params)
        self.logger.info(f"Skipping to next item: {res.get('result')}")

    def next_stream(self):
        """Cycle to the next audio stream in the currently playing file."""
        playerid = self.get_active_player()
        specific_params = {"method": "Player.SetAudioStream", "params": {"playerid": playerid, "stream": "next"}}
        res = self._runit(specific_params)
        self.logger.info(f"Skipping to next stream: {res.get('result')}")

    def subs_off(self):
        """Turn subtitles off."""
        playerid = self.get_active_player()
        specific_params = {
            "method": "Player.SetSubtitle",
            "params": {"playerid": playerid, "subtitle": "off", "enable": False},
        }
        res = self._runit(specific_params)
        self.logger.info(f"Dropping subtitles: {res.get('result')}")

    def subs_on(self):
        """Turn subtitles on, using the first availble subtitle."""
        playerid = self.get_active_player()
        specific_params = {
            "method": "Player.SetSubtitle",
            "params": {"playerid": playerid, "subtitle": "on", "enable": True},
        }
        res = self._runit(specific_params)
        self.logger.info(f"Enabling subtitles: {res.get('result')}")

    def loop_off(self):
        """Turn looping off."""
        playerid = self.get_active_player()
        specific_params = {
            "method": "Player.SetRepeat",
            "params": {"playerid": playerid, "repeat": "off"},
        }
        res = self._runit(specific_params)
        self.logger.info(f"Dropping subtitles: {res.get('result')}")

    def loop_on(self):
        """Turn looping on."""
        playerid = self.get_active_player() or 1
        specific_params = {
            "method": "Player.SetRepeat",
            "params": {"playerid": playerid, "repeat": "one"},
        }
        res = self._runit(specific_params)
        self.logger.info(f"Enabling subtitles: {res.get('result')}")

    def add_and_play(self, filename):  # pragma: no cover
        """Add a file to the current playlist and hit play (convenience function)."""
        if self.now_playing()[0]:
            self.add_to_playlist(filename)
        else:
            self.clear_playlists()
            self.add_to_playlist(filename)
            self.play_it(filename)
            # At this point, we should be playing, so hold until we can prove it.
            while self.get_active_player() is None:
                sleep(0.05)

    def get_audio_passthrough(self):
        """Fetch the current state of the audio passthrough setting."""
        specific_params = {"method": "Settings.GetSettingValue", "params": {"setting": "audiooutput.passthrough"}}
        res = self._runit(specific_params)
        return res.get("result", {}).get("value", False)

    def set_audio_passthrough(self, passtf):
        """Enable or disable audio passthrough based on the True/False of the passtf argument."""
        specific_params = {
            "method": "Settings.SetSettingValue",
            "params": {"setting": "audiooutput.passthrough", "value": bool(passtf)},
        }
        res = self._runit(specific_params)
        action = "Enabling" if bool(passtf) else "Disabling"
        self.logger.info(f"{action} passthrough: {res.get('result')}")

    def get_adjust_display_rate(self):
        """Fetch the current state of the adjust display rate setting."""
        specific_params = {"method": "Settings.GetSettingValue", "params": {"setting": "videoplayer.adjustrefreshrate"}}
        res = self._runit(specific_params)
        return res.get("result", {}).get("value", 0)

    def set_adjust_display_rate(self, adjusttf):
        """Enable or disable adjusting the display rate based on the True/False of the adjusttf argument."""
        specific_params = {
            "method": "Settings.SetSettingValue",
            "params": {"setting": "videoplayer.adjustrefreshrate", "value": 2 if bool(adjusttf) else 0},
        }
        res = self._runit(specific_params)
        action = "Enabling" if bool(adjusttf) else "Disabling"
        self.logger.info(f"{action} adjust display rate: {res.get('result')}")
