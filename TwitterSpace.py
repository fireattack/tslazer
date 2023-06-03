# tslazer.py
# Author: ef1500

import collections
import concurrent.futures
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse

import WebSocketHandler
from util import concat, requests_retry_session, safeify


class TwitterSpace:
    TwitterUser = collections.namedtuple('TwitterUser', ['name', 'screen_name', 'id'])

    @dataclass
    class SpacePlaylists:
        chunk_server: str
        dyn_url: str
        master_url: str
        chatToken: str

    @dataclass
    class Chunk:
        url: str
        filename: str

    @staticmethod
    def getUser(username):
        """
        Get Twitter User ID

        :param username: A Twitter User's @ handle
        :returns: TwitterUser NamedTuple
        """
        dataRequest = requests_retry_session().get(f"https://cdn.syndication.twimg.com/widgets/followbutton/info.json?screen_names={username}")
        dataResponse = dataRequest.json()
        return TwitterSpace.TwitterUser(dataResponse[0]['name'], dataResponse[0]['screen_name'], dataResponse[0]['id'])

    @staticmethod
    def getGuestToken():
        """
        Generate a guest token for use with the Twitter API. Note: Twitter will get mad if you call this too many times

        :returns: string
        """
        headers = {"authorization" : "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"}
        tokenRequest = requests_retry_session().post("https://api.twitter.com/1.1/guest/activate.json", headers=headers)
        tokenResponse = tokenRequest.json()
        return tokenResponse["guest_token"]

    @staticmethod
    def getPlaylists(media_key=None, guest_token=None, dyn_url=None):
        """
        Get The master playlist from a twitter space.

        :param media_key: The media key to the twitter space. Given in the metadata
        :param guest_token: The Guest Token that allows us to use the Twitter API without OAuth
        :param dyn_url: The dynamic/Master URL (If needed)
        :returns: NamedTuple SpacePlaylists
        """
        print(f'[DEBUG] Update playlist URLs...')
        if media_key != None and guest_token != None:
            headers = {"authorization" : "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA", "x-guest-token" : guest_token}
            dataRequest = requests_retry_session().get(f"https://twitter.com/i/api/1.1/live_video_stream/status/{media_key}", headers=headers)
            dataResponse = dataRequest.json()
            dataLocation = dataResponse['source']['location']
            dataLocation = re.sub(r"(dynamic_playlist\.m3u8((?=\?)(\?type=[a-z]{4,}))?|master_playlist\.m3u8(?=\?)(\?type=[a-z]{4,}))", "master_playlist.m3u8", dataLocation)

            chatToken = dataResponse["chatToken"]

        if dyn_url != None:
            dataLocation = dyn_url
            dataLocation = re.sub(r"(dynamic_playlist\.m3u8((?=\?)(\?type=[a-z]{4,}))?|master_playlist\.m3u8(?=\?)(\?type=[a-z]{4,}))", "master_playlist.m3u8", dataLocation)
            chatToken = "None"

        dataComponents = urlparse(dataLocation)

        # Prepare Data Path and Data Server
        # The data path is used to retrieve the True Master Playlist
        dataServer = f"{dataComponents.scheme}://{dataComponents.hostname}"
        dataPath = dataComponents.path

        # Get the Master Playlist
        playlistRequest = requests_retry_session().get(f"{dataServer}{dataPath}")
        playlistResponse = playlistRequest.text.split('\n')[-2]
        playlistUrl = f"{dataServer}{playlistResponse}"

        chunkServer = f"{dataServer}{dataPath[:-20]}"
#        return TwitterSpace.SpacePlaylists(chunkServer, f"{dataServer}{dataPath}" , playlistUrl, chatToken)
        if playlistResponse == "#EXT-X-ENDLIST":
            return TwitterSpace.SpacePlaylists(chunkServer[:-14], f"{dataServer}{dataPath}" , f"{dataServer}{dataPath}", chatToken)
        else:
            return TwitterSpace.SpacePlaylists(chunkServer, f"{dataServer}{dataPath}" , playlistUrl, chatToken)

    @staticmethod
    def getMetadata(space_id, guest_token):
        """
        Retrieve the Metadata for a given twitter space ID or URL.
        Note: If you are working with a dynamic url, then you cannot use this function.

        :param space_id: URL or Space ID
        :param guest_token: Guest Token
        """
        # print(f'[DEBUG] Get metadata for {space_id}...')
        try:
            spaceID = re.findall(r"\d[a-zA-Z]{12}", space_id)[0]
        except Exception:
            print("Unable to find a space ID, please try again.")

        # Prepare Variables
        headers = {"authorization" : "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA", "x-guest-token" : guest_token}
        variables = f"{{\"id\": \"{spaceID}\",\"isMetatagsQuery\":true,\"withSuperFollowsUserFields\":true,\"withDownvotePerspective\":false,\"withReactionsMetadata\":false,\"withReactionsPerspective\":false,\"withSuperFollowsTweetFields\":true,\"withReplays\":true}}"
        features = "{\"dont_mention_me_view_api_enabled\":true,\"interactive_text_enabled\":true,\"responsive_web_uc_gql_enabled\":false,\"vibe_tweet_context_enabled\":false,\"responsive_web_edit_tweet_api_enabled\":false,\"standardized_nudges_for_misinfo_nudges_enabled\":false}"

        metadataRequest = requests_retry_session().get(f"https://twitter.com/i/api/graphql/yMLYE2ltn1nOZ5Gyk3JYSw/AudioSpaceById?variables={variables}&features={features}", headers=headers)
        metadataResponse = metadataRequest.json()

        return metadataResponse

    @staticmethod
    def getChunks(playlists):
        """
        When we receive the chunks from the server, we want to be able to parse that m3u8 and get all of the chunks from it.

        :param playlists: space playlist namedtuple
        :returns: list of all chunks
        """

        while True:
        # it sometimes takes a very long time to update playlist in master_url. So we just constantly check it until it's updated.
            # update the playlist
            try:
                playlists = TwitterSpace.getPlaylists(dyn_url=playlists.dyn_url)
            except Exception:
                pass

            print(f'[DEBUG] current master_url filename: {playlists.master_url.split("/")[-1]}')
            print('[DEBUG] current master_url:')
            print(playlists.master_url)

            m3u8Request = requests_retry_session().get(playlists.master_url)
            print('[DEBUG] request status code:', m3u8Request.status_code)
            if m3u8Request.status_code != 200:
                print(f'[DEBUG] failed to get playlist m3u8, retry after 10 seconds...')
                time.sleep(10)
                continue
            m3u8Data = m3u8Request.text

            chunkList = list()
            for chunk in re.findall(r"chunk_\d{19}_\d+_a\.aac", m3u8Data):
                chunkList.append(TwitterSpace.Chunk(f"{playlists.chunk_server}{chunk}", chunk))

            print(f'[DEBUG] get {len(chunkList)} chunks.')
            if len(chunkList) > 0:
                break
            else:
                print(f'[DEBUG] failed to get any chunks, retry after 10 seconds...')
                time.sleep(10)
        return chunkList

    @staticmethod
    def downloadChunks(chunklist, filename, path='.', metadata=None):
        """
        Download all of the chunks from the m3u8 to a specified path.

        :param chunklist: list of chunks
        :param filename: Name of the file we want to write the data to
        :param path: the path to download the chunks to
        :param metadata: any additional metadata that we would like to write to the m4a
        :returns: None
        """
        path = Path(path)
        chunkpath = path / ('chunks_' + str(int(datetime.now().timestamp())) + '_' + filename)
        chunkpath.mkdir()

        def download(chunk, chunkpath):
            with requests_retry_session().get(chunk.url) as r:
                with (chunkpath / chunk.filename).open("wb") as chunkWriter:
                    chunkWriter.write(r.content)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            futures = [ex.submit(download, chunk, chunkpath) for chunk in chunklist]
            total = len(futures)
            finished = 0
            for _ in concurrent.futures.as_completed(futures):
                finished += 1
                print(f'\r{finished}/{total} chunks downloaded.      ', end='')

        print("\nFinished Downloading Chunks.")

        files = list(chunkpath.iterdir())
        temp_aac = path / f"{filename}_merged.aac"
        output = path / f"{filename}.m4a"
        concat(files, temp_aac)
        try:
            command = f"ffmpeg -loglevel error -stats -i \"{temp_aac}\" -c copy "
            if metadata != None:
                title = metadata["title"]
                author = metadata["author"]
                command += f"-metadata title=\"{title}\" -metadata artist=\"{author}\" "
            command += f"\"{output}\""
            print(f'[DEBUG] command is {command}')
            subprocess.run(command, shell=True)
        except Exception as e:
            print('Error when converting to m4a:')
            print(e)
            print(f'Temp files are saved at {chunkpath} and {temp_aac}.')
        else:
            # Delete the Directory with all of the chunks. We no longer need them.
            shutil.rmtree(chunkpath)
            temp_aac.unlink()
            print(f"Successfully Downloaded Twitter Space {filename}.m4a")

    def __init__(self, space_id=None, dyn_url=None, filename=None, filenameformat=None, path=None, withChat=False):
        self.space_id = space_id
        self.dyn_url = dyn_url
        self.filename = filename
        self.filenameformat = filenameformat
        self.path = path
        self.metadata = None
        self.playlists = None
        self.wasrunning = False

        # Get the metadata (If applicable)
        if self.space_id != None:
            guest_token = TwitterSpace.getGuestToken()
            self.metadata = TwitterSpace.getMetadata(self.space_id, guest_token)

        # If there's metadata, set the metadata.
        if self.metadata != None:

            try:
                self.title = self.metadata['data']['audioSpace']['metadata']['title']
            except Exception:
                self.title = self.metadata["data"]["audioSpace"]["metadata"]["creator_results"]["result"]["legacy"]["screen_name"].__add__("\'s space") # IF We couldn't get the space Title, just use twitter's default here.

            self.media_key = self.metadata["data"]["audioSpace"]["metadata"]["media_key"]
            self.state = self.metadata["data"]["audioSpace"]["metadata"]["state"]
            self.created_at = self.metadata["data"]["audioSpace"]["metadata"]["created_at"]
            self.started_at = self.metadata["data"]["audioSpace"]["metadata"]["started_at"]
            self.updated_at = self.metadata["data"]["audioSpace"]["metadata"]["updated_at"]
            try:
                self.creator = TwitterSpace.TwitterUser(self.metadata["data"]["audioSpace"]["metadata"]["creator_results"]["result"]["legacy"]["name"], self.metadata["data"]["audioSpace"]["metadata"]["creator_results"]["result"]["legacy"]["screen_name"], self.metadata["data"]["audioSpace"]["metadata"]["creator_results"]["result"]["rest_id"])
            except KeyError:
                self.creator = TwitterSpace.TwitterUser("Protected_User", "Protected", "0")

        # Get the Fileformat here, so that way it won't hinder the chat exporter when it's running.
        # Now let's format the fileformat per the user's request.
        # File Format Options:
        #    {host_display_name}	Host Display Name
        #    {host_username}	Host Username
        #    {host_user_id}	Host User ID
        #    {space_title}	Space Title
        #    {space_id}	Space ID
        #    {datetime}    Year-Month-Day Hour:Minute:Second (Local)
        #    {datetimeutc} Year-Month-Day Hour:Minute:Second (UTC)

        if self.filenameformat != None and self.metadata != None:
            substitutes = dict(
                host_display_name=self.creator.name,
                host_username=self.creator.screen_name,
                host_user_id=self.creator.id,
                space_title=self.title,
                space_id=self.space_id,
                datetime=datetime.now(),
                datetimeutc=datetime.now(timezone.utc),
            )
            self.filename = self.filenameformat.format(**substitutes)
            self.filename = safeify(self.filename)

        if not self.filename:
            self.filename = 'twitter_space_' + datetime.now().strftime('%Y%m%d_%H%M%S')

        # Now lets get the playlists
        if space_id != None and self.metadata != None:
            self.playlists = TwitterSpace.getPlaylists(media_key=self.media_key, guest_token=guest_token)
        if space_id == None and self.metadata == None:
            self.playlists = TwitterSpace.getPlaylists(dyn_url=self.dyn_url)

        # Now Start a subprocess for running the chat exporter
        if withChat == True and self.metadata != None:
            print("[ChatExporter] Chat Exporting is currently only supported for Ended Spaces with a recording. To Export Chat for a live space, copy the chat token and use WebSocketDriver.py.")
            chatThread = Thread(target=WebSocketHandler.SpaceChat, args=(self.playlists.chatToken, self.filename, self.path,))
            #chatThread.start()

        # Print out the Space Information and wait for the Space to End (if it's running)
        if self.metadata != None and self.state == "Running":
            self.wasrunning = True
            # Print out the space Information
            print(f"Space Found!")
            print(f"Space Title: {self.title}")
            print(f"Space Host Username: {self.creator.screen_name}")
            print(f"Space Host Display Name: {self.creator.name}")
            print(f"Space Master URL:\n{self.playlists.master_url}")
            print(f"Space Dynamic URL:\n{self.playlists.dyn_url}")
            print(f"Chat Token:\n{self.playlists.chatToken}")
            print(f"Downloading to {self.filename}.m4a")

            print("Waiting for space to end...")
            while self.state == "Running":
                self.metadata = TwitterSpace.getMetadata(self.space_id, guest_token)
                try:
                    self.state = self.metadata["data"]["audioSpace"]["metadata"]["state"]
                    time.sleep(10)
                except Exception:
                    self.state = "ERROR"
            print("Space Ended. Wait 1 minute for the recording to be processed.")
            time.sleep(60)

        print(f'[DEBUG] current master_url filename: {self.playlists.master_url.split("/")[-1]}')
        # Now it's time to download.

        if self.metadata != None:
            m4aMetadata = {"title" : self.title, "author" : self.creator.screen_name}
        else:
            m4aMetadata = None
        chunks = TwitterSpace.getChunks(self.playlists)
        TwitterSpace.downloadChunks(chunks, self.filename, self.path, m4aMetadata)

        if self.metadata != None and self.state == "Ended" and withChat == True and self.wasrunning == False:
            chatThread.start() # If We're Downloading a Recording, we're all good to download the chat.
            print("[ChatExporter]: Chat Thread Started")
