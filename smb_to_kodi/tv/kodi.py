from .models import Player
import requests
import logging


class Kodi:

    def __init__(self):
        self.url = Player.objects.get(pk=1).address
        self.struct = {"jsonrpc":"2.0", "id":"1", "method":"Player.Open", "params":{}}
        self.headers = {"Content-Type": "application/json"}
        self.logger = logging.getLogger("django")

    def _runit(self, specific_params):
        paramdict = self.struct.copy()
        paramdict.update(specific_params)
        try:
            r = requests.post(url=self.url, json=paramdict, headers=self.headers)
            return r.json()
        except requests.exceptions.ConnectionError:
            return {"result": {"connection": False}}

    def nowPlaying(self):
        specific_params = {"method": "Player.GetItem", "params": {"playerid":1, "properties": ["file"]}}
        r = self._runit(specific_params)
        try:
            playing_file = r["result"]["item"]["file"]
            assert bool(playing_file)
            return (True, playing_file)
        except:
            return (False, "None")

    def confirmSuccessfulPlay(self, filename):
        specific_params = {"method": "Playlist.GetItems", "params": {"playlistid":1, "properties": ["file"]}}
        r = self._runit(specific_params)
        try:
            files = [x["file"] for x in r["result"]["items"]]
            assert filename in files
        except:
            return False
        return self.nowPlaying()[0]

    def addToPlaylist(self, filename):
        specific_params = {"method": "Playlist.Add", "params": {"playlistid":1, "item":{"file":filename}}}
        r = self._runit(specific_params)
        o = r.get("result")
        if o and o == "OK":
            self.logger.info("Added {a} to playlist successfully!".format(a=filename))
        else:
            self.logger.error("PROBLEM: {a} not added to playlist. Try a different way.".format(a=filename))

    def listPlaylistItems(self):
        specific_params = {"method": "Playlist.GetItems", "params": {"playlistid":1, "properties": ["file"]}}
        r = self._runit(specific_params)
        print(r)

    def clearPlaylist(self):
        specific_params = {"method": "Playlist.Clear", "params": {"playlistid":1}}
        r = self._runit(specific_params)
        self.logger.info("Clearing playlist: %s" % r.get("result"))

    def playIt(self):
        specific_params = {"method": "Player.Open", "params": {"item":{"playlistid":1}}}
        r = self._runit(specific_params)
        self.logger.info("Playing: %s" % r.get("result"))

    def nextItem(self):
        specific_params = {"method": "Player.GoTo", "params": {"playerid":1, "to":"next"}}
        r = self._runit(specific_params)
        self.logger.info("Skipping to next stream: %s" % r.get("result"))

    def nextStream(self):
        specific_params = {"method": "Player.SetAudioStream", "params": {"playerid":1, "stream":"next"}}
        r = self._runit(specific_params)
        self.logger.info("Skipping to next stream: %s" % r.get("result"))

    def subsOff(self):
        specific_params = {"method": "Player.SetSubtitle", "params": {"playerid": 1, "subtitle": "off", "enable": False}}
        r = self._runit(specific_params)
        self.logger.info("Dropping subtitles: %s" % r.get("result"))

    def subsOn(self):
        specific_params = {"method": "Player.SetSubtitle", "params": {"playerid": 1, "subtitle": "on", "enable": True}}
        r = self._runit(specific_params)
        self.logger.info("Dropping subtitles: %s" % r.get("result"))

    def addAndPlay(self, filename):
        if self.nowPlaying()[0]:
            self.addToPlaylist(filename)
        else:
            self.clearPlaylist()
            self.addToPlaylist(filename)
            self.playIt()
