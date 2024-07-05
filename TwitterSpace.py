import collections
import concurrent.futures
import json
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread
from urllib.parse import urljoin

import WebSocketHandler
from utils import concat, load_cookie, requests_retry_session, safeify


TwitterUser = collections.namedtuple('TwitterUser', ['name', 'screen_name', 'id'])

class TwitterSpace:
    def get_user(self, username):
        """
        Get Twitter User ID

        :param username: A Twitter User's @ handle
        :returns: TwitterUser NamedTuple
        """
        dataRequest = self.session.get(f"https://cdn.syndication.twimg.com/widgets/followbutton/info.json?screen_names={username}")
        dataRequest.raise_for_status()
        dataResponse = dataRequest.json()
        return self.TwitterUser(dataResponse[0]['name'], dataResponse[0]['screen_name'], dataResponse[0]['id'])

    def get_guest_token(self):
        """
        Generate a guest token for use with the Twitter API. Note: Twitter will get mad if you call this too many times

        :returns: string
        """
        headers = {"authorization" : "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"}
        tokenRequest = self.session.post("https://api.twitter.com/1.1/guest/activate.json", headers=headers)
        tokenRequest.raise_for_status()
        tokenResponse = tokenRequest.json()
        return tokenResponse["guest_token"]

    def get_playlist(self, media_key):
        """
        Get The master playlist from a twitter space.

        :param media_key: The media key to the twitter space. Given in the metadata
        :returns: (playlist_url, chat_token)
        """
        dataRequest = self.session.get(f"https://twitter.com/i/api/1.1/live_video_stream/status/{media_key}")
        dataRequest.raise_for_status()
        dataResponse = dataRequest.json()
        dataLocation = dataResponse['source']['location']
        chatToken = dataResponse["chatToken"]

        return dataLocation, chatToken

    def get_metadata(self, space_id):
        """
        Retrieve the Metadata for a given twitter space ID or URL.
        Note: If you are working with a dynamic url, then you cannot use this function.

        :returns: dict
        """
        # print(f'[DEBUG] Get metadata for {space_id}...')
        # https://x.com/i/broadcasts/1BRJjPBzbbBKw
        if m := re.search(r"/i/broadcasts/(\d[a-zA-Z]{12})", space_id):
            space_id = m[1]
            self.type = 'video'
        elif m := re.search(r"/i/spaces/(\d[a-zA-Z]{12})", space_id):
            space_id = m[1]
            self.type = 'audio'
        else:
            assert re.search(r"^\d[a-zA-Z]{12}$", space_id), f"Invalid space ID: {space_id}"
        self.space_id = space_id

        if self.type == 'audio':
            variables = {
                "id": space_id,
                "isMetatagsQuery": True,
                "withSuperFollowsUserFields": True,
                "withDownvotePerspective": False,
                "withReactionsMetadata": False,
                "withReactionsPerspective": False,
                "withSuperFollowsTweetFields": True,
                "withReplays": True
            }
            features = {
                "dont_mention_me_view_api_enabled": True,
                "interactive_text_enabled": True,
                "responsive_web_uc_gql_enabled": False,
                "vibe_tweet_context_enabled": False,
                "responsive_web_edit_tweet_api_enabled": False,
                "standardized_nudges_for_misinfo_nudges_enabled": False
            }
            url = "https://twitter.com/i/api/graphql/yMLYE2ltn1nOZ5Gyk3JYSw/AudioSpaceById"

        else:
            variables = {
                "id": space_id
            }
            features = {
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "communities_web_enable_tweet_community_results_fetch": True,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
                "articles_preview_enabled": True,
                "rweb_tipjar_consumption_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "tweetypie_unmention_optimization_enabled": True,
                "responsive_web_edit_tweet_api_enabled": True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                "view_counts_everywhere_api_enabled": True,
                "longform_notetweets_consumption_enabled": True,
                "responsive_web_twitter_article_tweet_consumption_enabled": True,
                "tweet_awards_web_tipping_enabled": False,
                "creator_subscriptions_quote_tweet_preview_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "rweb_video_timestamps_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_enhance_cards_enabled": False
            }
            url = "https://x.com/i/api/graphql/Ft426awxxM1206ZcaShbDw/BroadcastQuery"

        variables_str = json.dumps(variables)
        features_str = json.dumps(features)
        params = {"variables": variables_str, "features": features_str}

        metadataRequest = self.session.get(url, params=params)
        metadataRequest.raise_for_status()
        metadataResponse = metadataRequest.json()

        return metadataResponse

    def get_chunks(self, playlist_url):
        """
        When we receive the chunks from the server, we want to be able to parse that m3u8 and get all of the chunks from it.

        :param playlists: space playlist url, either master_playlist or playlist_\\d+ (for replay)
        :returns: list of all chunks
        """

        if 'master_playlist.m3u8' in playlist_url or 'master_dynamic_' in playlist_url:
            print('[DEBUG] fetch sub playlist from master playlist...')
            while True:
                r = self.session.get(playlist_url)
                real_playlist_url = urljoin(playlist_url, r.text.split('\n')[-2])
                playlist_name = real_playlist_url.split("/")[-1]
                print(f'[DEBUG] current playlist_url is: {playlist_name}')
                m3u8Request = self.session.get(real_playlist_url)
                print('[DEBUG] request status code:', m3u8Request.status_code)
                if m3u8Request.status_code == 200:
                    break
                print(f'[DEBUG] failed to get {playlist_name} ({m3u8Request.status_code}), retry after 10 seconds...')
                time.sleep(10)
        else:
            m3u8Request = self.session.get(playlist_url)
        m3u8Data = m3u8Request.text

        chunkList = list()
        for chunk in re.findall(r"chunk_\d{19}_\d+_a\.(?:aac|ts)", m3u8Data):
            chunkList.append(urljoin(playlist_url, chunk)) # use playlist_url, NOT real_playlist_url

        print(f'[DEBUG] get {len(chunkList)} chunks.')
        assert len(chunkList) > 0, "No chunks found in m3u8"
        return chunkList

    def download_chunks(self, chunklist, filename, path='.', metadata=None, keep_temp=False):
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
            f = chunk_dir / filename
            retry_count = 0
            while retry_count < 10:
                if retry_count > 0:
                    print(f"Retry {retry_count} for {filename}...")
                try:
                    with self.session.get(chunk_url, timeout=8) as r:
                        r.raise_for_status()
                        expected_size = int(r.headers.get('Content-Length', -1))
                        if expected_size < 0:
                            raise Exception(f"Failed to get Content-Length for {filename}")
                        with f.open("wb") as chunkWriter:
                            chunkWriter.write(r.content)
                        actual_size = f.stat().st_size
                        if actual_size == expected_size:
                            break
                        else:
                            print(f"\{filename} size mismatch: expected {expected_size}, got {actual_size}")
                            retry_count += 1
                except Exception as e:
                    print(f"\nError downloading chunk: {e}")
                    retry_count += 1
            else:
                raise Exception(f"Failed to download chunk {filename} after 10 retries")

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.threads) as ex:
            futures = [ex.submit(download, chunk_url, chunk_dir) for chunk_url in chunklist]
            total = len(futures)
            finished = 0
            try:
                for future in concurrent.futures.as_completed(futures):
                    if future.exception() is not None:
                        print('\nFatal error:', future.exception())
                        for future in futures:
                            future.cancel()
                        return
                    finished += 1
                    print(f'\r{finished}/{total} chunks downloaded.      ', end='')
            except KeyboardInterrupt:
                print("\nDownload interrupted by user. Aborting...")
                for future in futures:
                    future.cancel()
                return

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

        self.type == 'video' if files[0].suffix == '.ts' else 'audio'
        if self.type == 'video':
            output = path / f"{filename}.ts"
            temp = None
            print("Merging chunks using binary concat...")
            concat(files, output)
            # do not try to convert to mp4.
            # Twitter uses non-standard mpeg-ts container, which often causes issues with ffmpeg.
        else:
            temp = path / f"{filename}_merged.aac"
            output = path / f"{filename}.m4a"
            print("Merging chunks using binary concat...")
            concat(files, temp)
            print("Remuxing to m4a using FFMPEG...")
            try:
                command = f"ffmpeg -loglevel error -stats -i \"{temp}\" -c copy "
                if metadata != None:
                    title = metadata["title"]
                    author = metadata["author"]
                    command += f"-metadata title=\"{title}\" -metadata artist=\"{author}\" "
                command += f"\"{output}\""
                print(f'[DEBUG] command is {command}')
                r = subprocess.run(command, shell=True)
                r.check_returncode()
            except Exception as e:
                print('Error when converting to m4a:')
                print(e)
                print(f'Temp files are saved at {chunk_dir} and {temp}.')
                return

        # Delete the Directory with all of the chunks. We no longer need them.
        if keep_temp:
            print(f'--keep is enabled. Temp files are saved at {chunk_dir} and {temp}.')
        else:
            shutil.rmtree(chunk_dir)
            if temp:
                temp.unlink()
        print(f"Successfully Downloaded Twitter Space at {output}")

    def set_headers(self, guest_token=None, cookies=None):
        """
        Constructs and returns the headers for Twitter API HTTP requests.

        :param guest_token: A string representing the guest token. Default is None.
        :param cookies: A dictionary of cookie name-value pairs. Default is None.

        :assert: Either guest_token or cookies must be provided.

        :return: A dictionary containing the headers for the request.

        :raises AssertionError: If both guest_token and cookies are None.
        """
        assert guest_token is not None or cookies is not None, 'guest_token or cookies must be provided.'
        if guest_token:
            self.session.headers.update({
                "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
                "x-guest-token": guest_token
            })
        else:
            cookie_header = "; ".join([f"{name}={value}" for name, value in cookies.items()])
            self.session.headers.update({
                "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
                "x-csrf-token": cookies['ct0'],
                "cookie": cookie_header
            })

    def __init__(self, space_id=None, dyn_url=None, filename=None, filenameformat=None, path=None,
                 with_chat=False, keep_temp=False, cookies=None, type_='audio', simulate=False, threads=20):
        self.space_id = space_id
        self.dyn_url = dyn_url
        self.filename = filename
        self.filenameformat = filenameformat
        self.path = path
        self.metadata = None
        self.playlists = None
        self.was_running = False
        self.keep_temp = keep_temp
        self.cookies = cookies
        self.type = type_
        self.threads = threads
        self.session = requests_retry_session()

        if self.space_id is not None:
            if self.cookies is None:
                # guest_token = self.getGuestToken()
                print('[Error] Download from a Space ID without cookies is no longer supported.')
                return
            cookies = load_cookie(self.cookies)
            self.set_headers(cookies=cookies)
            self.metadata = self.get_metadata(self.space_id)
            if 'errors' in self.metadata:
                print(f"Error: {self.metadata['errors'][0]['message']}")
                return
            if self.type == 'audio':
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
                    self.creator = TwitterUser(
                        self.metadata["data"]["audioSpace"]["metadata"]["creator_results"]["result"]["legacy"]["name"],
                        self.metadata["data"]["audioSpace"]["metadata"]["creator_results"]["result"]["legacy"]["screen_name"],
                        self.metadata["data"]["audioSpace"]["metadata"]["creator_results"]["result"]["rest_id"]
                        )
                except KeyError:
                    self.creator = TwitterUser("Protected_User", "Protected", "0")
            else:
                self.title = self.metadata['data']['broadcast']['status']
                self.media_key = self.metadata['data']['broadcast']['media_key']
                self.state = self.metadata['data']['broadcast']['state']
                self.started_at = self.metadata['data']['broadcast']['start_time']
                try:
                    self.creator = TwitterUser(
                        self.metadata['data']['broadcast']['user_results']["result"]["legacy"]['name'],
                        self.metadata['data']['broadcast']['user_results']["result"]["legacy"]["screen_name"],
                        self.metadata['data']['broadcast']['user_results']["result"]["rest_id"]
                        )
                except KeyError:
                    self.creator = TwitterUser("Protected_User", "Protected", "0")

            self.playlist_url, self.chat_token = self.get_playlist(self.media_key)

            # Get the Filename Format here, so that way it won't hinder the chat exporter when it's running.
            # Now let's format the `filenameformat` per the user's request.
            # File Format Options:
            #    {host_display_name} Host Display Name
            #    {host_username}     Host Username
            #    {host_user_id}      Host User ID
            #    {space_title}       Space Title
            #    {space_id}          Space ID
            #    {datetime}          Space Start Time (Local)
            #    {datetimeutc}       Space Start Time (UTC)
            #    {type}              Type of the livestream (space or broadcast)
            if self.filenameformat is not None and self.filename is None:
                substitutes = dict(
                    host_display_name=self.creator.name,
                    host_username=self.creator.screen_name,
                    host_user_id=self.creator.id,
                    space_title=self.title,
                    space_id=self.space_id,
                    datetime=datetime.fromtimestamp(self.started_at/1000.0),
                    datetimeutc=datetime.fromtimestamp(self.started_at/1000.0, tz=timezone.utc),
                    type='space' if self.type == 'audio' else 'broadcast'
                )
                self.filename = self.filenameformat.format(**substitutes)
                self.filename = safeify(self.filename)

        # this is when the user provides a dynamic url
        else:
            assert self.dyn_url is not None, "No URL provided"
            self.type = 'audio' if '/audio-space/' in self.dyn_url else 'video'
            self.playlist_url = self.dyn_url

        # fetch the static master playlist, if the input isn't a sub-playlist already.
        self.playlist_url = re.sub(r"(dynamic_playlist\.m3u8((?=\?)(\?type=[a-z]{4,}))?|master_(dynamic_)?playlist\.m3u8(?=\?)(\?type=[a-z]{4,}))", "master_playlist.m3u8", self.playlist_url)

        # if filename hasn't been set, set it to the default.
        type_name = 'space' if self.type == 'audio' else 'broadcast'
        if not self.filename:
            self.filename = f'twitter_{type_name}_' + datetime.now().strftime('%Y%m%d_%H%M%S')

        # Now Start a subprocess for running the chat exporter
        if with_chat == True and self.metadata is not None and self.type == 'audio':
            print("[ChatExporter] Chat Exporting is currently only supported for Ended Spaces with a recording. To Export Chat for a live space, copy the chat token and use WebSocketDriver.py.")
            chatThread = Thread(target=WebSocketHandler.SpaceChat, args=(self.chat_token, self.filename, self.path,))
            #chatThread.start()

        # Print out the Space Information and wait for the Space to End (if it's running)
        if self.metadata is not None:
            # Print out the space Information
            type_name = type_name.capitalize()
            suffix = '.ts' if self.type == 'video' else '.m4a'
            print(f"{type_name} Found!")
            print(f"{type_name} ID: {self.space_id}")
            print(f"{type_name} Title: {self.title}")
            print(f'{type_name} Current State: {self.state}')
            print(f"{type_name} Host Username: {self.creator.screen_name}")
            print(f"{type_name} Host Display Name: {self.creator.name}")
            print(f"{type_name} Playlist URL:\n{self.playlist_url}")
            print(f"Chat Token:\n{self.chat_token}")
            print(f"Downloading to {self.filename}{suffix}")
            if self.state == "Running":
                self.was_running = True
                print("Waiting for space to end...")
                while self.state == "Running":
                    self.metadata = self.get_metadata(self.space_id)
                    try:
                        #TODO: live download;
                        #TODO: check if it works for broadcast/video
                        self.state = self.metadata["data"]["audioSpace"]["metadata"]["state"] if self.type == 'audio' else self.metadata['data']['broadcast']['state']
                        time.sleep(10)
                    except Exception:
                        self.state = "ERROR"
                print("Space Ended. Wait 1 minute for the recording to be processed.")
                time.sleep(60)
        if self.metadata is not None:
            m4aMetadata = {"title" : self.title, "author" : self.creator.screen_name}
        else:
            m4aMetadata = None

        chunks = self.get_chunks(self.playlist_url)
        if simulate:
            print("Simulate mode, no download will be performed.")
            return
        self.download_chunks(chunks, self.filename, self.path, m4aMetadata, keep_temp=self.keep_temp)

        if self.metadata is not None and self.state == "Ended" and with_chat == True and self.was_running == False:
            chatThread.start() # If We're Downloading a Recording, we're all good to download the chat.
            print("[ChatExporter]: Chat Thread Started")
