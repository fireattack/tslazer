# tslazer.py
# Author: ef1500

import collections
import concurrent.futures
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread
from urllib.parse import urljoin

import WebSocketHandler
from util import concat, requests_retry_session, safeify


class TwitterSpace:
    TwitterUser = collections.namedtuple('TwitterUser', ['name', 'screen_name', 'id'])

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
    def getPlaylist(media_key, guest_token):
        """
        Get The master playlist from a twitter space.

        :param media_key: The media key to the twitter space. Given in the metadata
        :param guest_token: The Guest Token that allows us to use the Twitter API without OAuth
        :returns: (playlist_url, chat_token)
        """
        headers = {"authorization" : "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA", "x-guest-token" : guest_token}
        dataRequest = requests_retry_session().get(f"https://twitter.com/i/api/1.1/live_video_stream/status/{media_key}", headers=headers)
        dataResponse = dataRequest.json()
        dataLocation = dataResponse['source']['location']
        chatToken = dataResponse["chatToken"]

        return dataLocation, chatToken

    @staticmethod
    def getMetadata(space_id, guest_token):
        """
        Retrieve the Metadata for a given twitter space ID or URL.
        Note: If you are working with a dynamic url, then you cannot use this function.

        :param space_id: URL or Space ID
        :param guest_token: Guest Token
        :returns: dict
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
    def getChunks(playlist_url):
        """
        When we receive the chunks from the server, we want to be able to parse that m3u8 and get all of the chunks from it.

        :param playlists: space playlist url, either master_playlist or playlist_\d+ (for replay)
        :returns: list of all chunks
        """
        # when fetching from a recording, the playlist url looks like this:
        # https://prod-fastly-ap-northeast-1.video.pscp.tv/Transcoding/v1/hls/{somehash}/non_transcode/ap-northeast-1/periscope-replay-direct-prod-ap-northeast-1-public/audio-space/playlist_16760776723829618751.m3u8?type=replay

        # when fetching from a live space, the playlist url looks like this:
        # https://prod-fastly-ap-northeast-1.video.pscp.tv/Transcoding/v1/hls/{somehash}/non_transcode/ap-northeast-1/periscope-replay-direct-prod-ap-northeast-1-public/audio-space/master_playlist.m3u8
        # which has a sub playlist like this:
        # https://prod-fastly-ap-northeast-1.video.pscp.tv/Transcoding/v1/hls/{somehash}/transcode/ap-northeast-1/periscope-replay-direct-prod-ap-northeast-1-public/{someconfig}/audio-space/playlist_16761019244202992663.m3u8
        # sometimes this sub playlist is 404, you need to wait for a while and try again.
        # and when get chunks, join its name to the BASE master_playlist.m3u8's URL (the one with /non_transcode/), NOT the sub playlist one (the one with /transcode/{someconfig}/}).

        if 'master_playlist.m3u8' in playlist_url:
            print('[DEBUG] fetch sub playlist from master playlist...')
            while True:
                r = requests_retry_session().get(playlist_url)
                real_playlist_url = urljoin(playlist_url, r.text.split('\n')[-2])
                playlist_name = real_playlist_url.split("/")[-1]
                print(f'[DEBUG] current playlist_url is: {playlist_name}')
                m3u8Request = requests_retry_session().get(real_playlist_url)
                print('[DEBUG] request status code:', m3u8Request.status_code)
                if m3u8Request.status_code == 200:
                    break
                print(f'[DEBUG] failed to get {playlist_name} ({m3u8Request.status_code}), retry after 10 seconds...')
                time.sleep(10)
        else:
            m3u8Request = requests_retry_session().get(playlist_url)
        m3u8Data = m3u8Request.text

        chunkList = list()
        for chunk in re.findall(r"chunk_\d{19}_\d+_a\.aac", m3u8Data):
            chunkList.append(urljoin(playlist_url, chunk)) # use playlist_url, NOT real_playlist_url

        print(f'[DEBUG] get {len(chunkList)} chunks.')
        assert len(chunkList) > 0, "No chunks found in m3u8"
        return chunkList

    @staticmethod
    def downloadChunks(chunklist, filename, path='.', metadata=None, keep_temp=False):
        """
        Download all of the chunks from the m3u8 to a specified path.

        :param chunklist: list of chunks
        :param filename: Name of the file we want to write the data to
        :param path: the path to download the chunks to
        :param metadata: any additional metadata that we would like to write to the m4a
        :param keep_temp: keep the temp files
        :returns: None
        """
        path = Path(path)
        chunk_dir = path / ('chunks_' + str(int(datetime.now().timestamp())) + '_' + filename)
        chunk_dir.mkdir()

        def download(chunk_url, chunk_dir):
            filename = chunk_url.split("/")[-1]
            with requests_retry_session().get(chunk_url) as r:
                with (chunk_dir / filename).open("wb") as chunkWriter:
                    chunkWriter.write(r.content)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            futures = [ex.submit(download, chunk_url, chunk_dir) for chunk_url in chunklist]
            total = len(futures)
            finished = 0
            for future in concurrent.futures.as_completed(futures):
                if future.exception() is not None:
                    print(future.exception())
                finished += 1
                print(f'\r{finished}/{total} chunks downloaded.      ', end='')

        print("\nFinished Downloading Chunks.")

        # Verify, and the files will be automatically in order
        files = []
        for chunk_url in chunklist:
            f = chunk_dir / chunk_url.split("/")[-1]
            assert f.exists(), f"Chunk {f.name} does not exist!"
            files.append(f)

        if keep_temp:
            # generate a list of files
            s = '\n'.join([f.name for f in files])
            Path('chunks_debug.txt').write_text(s, encoding='utf-8')

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
            print(f'Temp files are saved at {chunk_dir} and {temp_aac}.')
        else:
            # Delete the Directory with all of the chunks. We no longer need them.
            if keep_temp:
                print(f'Keep mode. Temp files are saved at {chunk_dir} and {temp_aac}.')
            else:
                shutil.rmtree(chunk_dir)
                temp_aac.unlink()
            print(f"Successfully Downloaded Twitter Space {filename}.m4a")

    def __init__(self, space_id=None, dyn_url=None, filename=None, filenameformat=None, path=None, withChat=False, keep_temp=False):
        self.space_id = space_id
        self.dyn_url = dyn_url
        self.filename = filename
        self.filenameformat = filenameformat
        self.path = path
        self.metadata = None
        self.playlists = None
        self.wasrunning = False
        self.keep_temp = keep_temp

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
        #    {host_display_name} Host Display Name
        #    {host_username}     Host Username
        #    {host_user_id}      Host User ID
        #    {space_title}       Space Title
        #    {space_id}          Space ID
        #    {datetime}          Year-Month-Day Hour:Minute:Second (Local)
        #    {datetimeutc}       Year-Month-Day Hour:Minute:Second (UTC)

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
            self.playlist_url, self.chat_token = TwitterSpace.getPlaylist(media_key=self.media_key, guest_token=guest_token)
        else:
            self.playlist_url = self.dyn_url
        self.playlist_url = re.sub(r"(dynamic_playlist\.m3u8((?=\?)(\?type=[a-z]{4,}))?|master_playlist\.m3u8(?=\?)(\?type=[a-z]{4,}))", "master_playlist.m3u8", self.playlist_url)

        # Now Start a subprocess for running the chat exporter
        if withChat == True and self.metadata != None:
            print("[ChatExporter] Chat Exporting is currently only supported for Ended Spaces with a recording. To Export Chat for a live space, copy the chat token and use WebSocketDriver.py.")
            chatThread = Thread(target=WebSocketHandler.SpaceChat, args=(self.chat_token, self.filename, self.path,))
            #chatThread.start()

        # Print out the Space Information and wait for the Space to End (if it's running)
        if self.metadata != None and self.state == "Running":
            self.wasrunning = True
            # Print out the space Information
            print(f"Space Found!")
            print(f"Space Title: {self.title}")
            print(f"Space Host Username: {self.creator.screen_name}")
            print(f"Space Host Display Name: {self.creator.name}")
            print(f"Space Playlist URL:\n{self.playlist_url}")
            print(f"Chat Token:\n{self.chat_token}")
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

        if self.metadata != None:
            m4aMetadata = {"title" : self.title, "author" : self.creator.screen_name}
        else:
            m4aMetadata = None
        chunks = TwitterSpace.getChunks(self.playlist_url)
        TwitterSpace.downloadChunks(chunks, self.filename, self.path, m4aMetadata, keep_temp=self.keep_temp)

        if self.metadata != None and self.state == "Ended" and withChat == True and self.wasrunning == False:
            chatThread.start() # If We're Downloading a Recording, we're all good to download the chat.
            print("[ChatExporter]: Chat Thread Started")
