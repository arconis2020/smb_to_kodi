"""A module to control a Kodi/XMBC media player over the network using JSONRPC."""
from .models import Player
import requests
import logging


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
            r = requests.post(url=self.url, json=paramdict, headers=self.headers)
            return r.json()
        except requests.exceptions.ConnectionError:
            return {"result": {"connection": False}}

    def nowPlaying(self):
        """Obtain the name of the currently playing item, if any, and confirm the player is playing."""
        specific_params = {"method": "Player.GetItem", "params": {"playerid": 1, "properties": ["file"]}}
        r = self._runit(specific_params)
        try:
            playing_file = r["result"]["item"]["file"]
            assert bool(playing_file)
            return (True, playing_file)
        except (TypeError, AssertionError):
            return (False, "None")

    def confirmSuccessfulPlay(self, filename):
        """Confirm that the filename is in the current playlist, and that the player is playing."""
        specific_params = {"method": "Playlist.GetItems", "params": {"playlistid": 1, "properties": ["file"]}}
        r = self._runit(specific_params)
        try:
            files = [x["file"] for x in r["result"]["items"]]
            assert filename in files
        except (TypeError, AssertionError):
            return False
        return self.nowPlaying()[0]

    def addToPlaylist(self, filename):
        """Add the filename (str) to the current playlist."""
        specific_params = {"method": "Playlist.Add", "params": {"playlistid": 1, "item": {"file": filename}}}
        r = self._runit(specific_params)
        o = r.get("result")
        if o and o == "OK":
            self.logger.info("Added {a} to playlist successfully!".format(a=filename))
        else:
            self.logger.error("PROBLEM: {a} not added to playlist. Try a different way.".format(a=filename))

    def listPlaylistItems(self):
        """List all current playlist items."""
        specific_params = {"method": "Playlist.GetItems", "params": {"playlistid": 1, "properties": ["file"]}}
        r = self._runit(specific_params)

    def clearPlaylist(self):
        """Clear the current playlist."""
        specific_params = {"method": "Playlist.Clear", "params": {"playlistid": 1}}
        r = self._runit(specific_params)
        self.logger.info("Clearing playlist: %s" % r.get("result"))

    def playIt(self):
        """Press the play button, likely playing the first item in the current playlist."""
        specific_params = {"method": "Player.Open", "params": {"item": {"playlistid": 1}}}
        r = self._runit(specific_params)
        self.logger.info("Playing: %s" % r.get("result"))

    def nextItem(self):
        """Advance to the next item in the current playlist."""
        specific_params = {"method": "Player.GoTo", "params": {"playerid": 1, "to": "next"}}
        r = self._runit(specific_params)
        self.logger.info("Skipping to next stream: %s" % r.get("result"))

    def nextStream(self):
        """Cycle to the next audio stream in the currently playing file."""
        specific_params = {"method": "Player.SetAudioStream", "params": {"playerid": 1, "stream": "next"}}
        r = self._runit(specific_params)
        self.logger.info("Skipping to next stream: %s" % r.get("result"))

    def subsOff(self):
        """Turn subtitles off."""
        specific_params = {
            "method": "Player.SetSubtitle",
            "params": {"playerid": 1, "subtitle": "off", "enable": False},
        }
        r = self._runit(specific_params)
        self.logger.info("Dropping subtitles: %s" % r.get("result"))

    def subsOn(self):
        """Turn subtitles on, using the first availble subtitle."""
        specific_params = {"method": "Player.SetSubtitle", "params": {"playerid": 1, "subtitle": "on", "enable": True}}
        r = self._runit(specific_params)
        self.logger.info("Dropping subtitles: %s" % r.get("result"))

    def addAndPlay(self, filename):
        """Add a file to the current playlist and hit play (convenience function)."""
        if self.nowPlaying()[0]:
            self.addToPlaylist(filename)
        else:
            self.clearPlaylist()
            self.addToPlaylist(filename)
            self.playIt()

    def setAudioPassthrough(self, passtf):
        """Enable or disable audio passthrough based on the True/False of the passtf argument."""
        specific_params = {
            "method": "Settings.SetSettingValue",
            "params": {"setting": "audiooutput.passthrough", "value": bool(passtf)},
        }
        r = self._runit(specific_params)
        self.logger.info("{0} passthrough: {1}".format("Enabling" if bool(passtf) else "Disabling", r.get("result")))
