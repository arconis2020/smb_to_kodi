"""A module to control a Kodi/XMBC media player over the network using JSONRPC."""
import logging
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
            res = requests.post(url=self.url, json=paramdict, headers=self.headers, timeout=30)
            return res.json()
        except requests.exceptions.ConnectionError:
            return {"result": {"connection": False}}

    def now_playing(self):
        """Obtain the name of the currently playing item, if any, and confirm the player is playing."""
        specific_params = {"method": "Player.GetItem", "params": {"playerid": 1, "properties": ["file"]}}
        res = self._runit(specific_params)
        try:
            playing_file = res["result"]["item"]["file"]
            assert bool(playing_file)
            return (True, playing_file)
        except (KeyError, AssertionError):
            return (False, "None")

    def confirm_successful_play(self, filename):
        """Confirm that the filename is in the current playlist, and that the player is playing."""
        specific_params = {"method": "Playlist.GetItems", "params": {"playlistid": 1, "properties": ["file"]}}
        res = self._runit(specific_params)
        try:
            files = [x["file"] for x in res["result"]["items"]]
            assert filename in files
        except (KeyError, AssertionError):
            return False
        return self.now_playing()[0]

    def add_to_playlist(self, filename):
        """Add the filename (str) to the current playlist."""
        specific_params = {"method": "Playlist.Add", "params": {"playlistid": 1, "item": {"file": filename}}}
        res = self._runit(specific_params)
        out = res.get("result")
        if out and out == "OK":
            self.logger.info(f"Added {filename} to playlist successfully!")
        else:
            self.logger.error(f"PROBLEM: {filename} not added to playlist. Try a different way.")

    def clear_playlist(self):
        """Clear the current playlist."""
        specific_params = {"method": "Playlist.Clear", "params": {"playlistid": 1}}
        res = self._runit(specific_params)
        self.logger.info(f"Clearing playlist: {res.get('result')}")

    def play_it(self):
        """Press the play button, likely playing the first item in the current playlist."""
        specific_params = {"method": "Player.Open", "params": {"item": {"playlistid": 1}}}
        res = self._runit(specific_params)
        self.logger.info(f"Playing: {res.get('result')}")

    def next_item(self):
        """Advance to the next item in the current playlist."""
        specific_params = {"method": "Player.GoTo", "params": {"playerid": 1, "to": "next"}}
        res = self._runit(specific_params)
        self.logger.info(f"Skipping to next item: {res.get('result')}")

    def next_stream(self):
        """Cycle to the next audio stream in the currently playing file."""
        specific_params = {"method": "Player.SetAudioStream", "params": {"playerid": 1, "stream": "next"}}
        res = self._runit(specific_params)
        self.logger.info(f"Skipping to next stream: {res.get('result')}")

    def subs_off(self):
        """Turn subtitles off."""
        specific_params = {
            "method": "Player.SetSubtitle",
            "params": {"playerid": 1, "subtitle": "off", "enable": False},
        }
        res = self._runit(specific_params)
        self.logger.info(f"Dropping subtitles: {res.get('result')}")

    def subs_on(self):
        """Turn subtitles on, using the first availble subtitle."""
        specific_params = {"method": "Player.SetSubtitle", "params": {"playerid": 1, "subtitle": "on", "enable": True}}
        res = self._runit(specific_params)
        self.logger.info(f"Enabling subtitles: {res.get('result')}")

    def add_and_play(self, filename):  # pragma: no cover
        """Add a file to the current playlist and hit play (convenience function)."""
        if self.now_playing()[0]:
            self.add_to_playlist(filename)
        else:
            self.clear_playlist()
            self.add_to_playlist(filename)
            self.play_it()

    def get_audio_passthrough(self):
        """Fetch the current state of the audio passthrough setting."""
        specific_params = {"method": "Settings.GetSettingValue", "params": {"setting": "audiooutput.passthrough"}}
        res = self._runit(specific_params)
        return res.get("result").get("value", False)

    def set_audio_passthrough(self, passtf):
        """Enable or disable audio passthrough based on the True/False of the passtf argument."""
        specific_params = {
            "method": "Settings.SetSettingValue",
            "params": {"setting": "audiooutput.passthrough", "value": bool(passtf)},
        }
        res = self._runit(specific_params)
        action = "Enabling" if bool(passtf) else "Disabling"
        self.logger.info(f"{action} passthrough: {res.get('result')}")
