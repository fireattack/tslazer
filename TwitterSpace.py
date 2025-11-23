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

import m3u8

import WebSocketHandler
from utils import concat, decode, load_cookie, requests_retry_session, safeify

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

    def parse_url_or_space_id(self, url_or_space_id):
        if m := re.search(r"/i/broadcasts/(\d[a-zA-Z]{12})", url_or_space_id):
            space_id = m[1]
            self.type = 'broadcast'
        elif m := re.search(r"/i/spaces/(\d[a-zA-Z]{12})", url_or_space_id):
            space_id = m[1]
            self.type = 'space'
        else:
            assert re.search(r"^\d[a-zA-Z]{12}$", url_or_space_id), f"Invalid ID or URL: {url_or_space_id}"
            space_id = url_or_space_id
        self.space_id = space_id

    def get_metadata(self, space_id):
        """
        Retrieve the Metadata for a given twitter space ID or URL.
        Note: If you are working with a dynamic url, then you cannot use this function.

        :returns: dict
        """
        if self.type == 'space':
            variables = {
                "id": space_id,
                "isMetatagsQuery": True,
                "withReplays": True,
                "withListeners": True
            }
            features = {
                "spaces_2022_h2_spaces_communities": True,
                "spaces_2022_h2_clipping": True,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "profile_label_improvements_pcf_label_in_post_enabled": True,
                "responsive_web_profile_redirect_enabled": False,
                "rweb_tipjar_consumption_enabled": True,
                "verified_phone_label_enabled": False,
                "premium_content_api_read_enabled": False,
                "communities_web_enable_tweet_community_results_fetch": True,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
                "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
                "responsive_web_grok_analyze_post_followups_enabled": True,
                "responsive_web_jetfuel_frame": True,
                "responsive_web_grok_share_attachment_enabled": True,
                "articles_preview_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "responsive_web_edit_tweet_api_enabled": True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                "view_counts_everywhere_api_enabled": True,
                "longform_notetweets_consumption_enabled": True,
                "responsive_web_twitter_article_tweet_consumption_enabled": True,
                "tweet_awards_web_tipping_enabled": False,
                "responsive_web_grok_show_grok_translated_post": False,
                "responsive_web_grok_analysis_button_from_backend": True,
                "creator_subscriptions_quote_tweet_preview_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "responsive_web_grok_image_annotation_enabled": True,
                "responsive_web_grok_imagine_annotation_enabled": True,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_grok_community_note_auto_translation_is_enabled": False,
                "responsive_web_enhance_cards_enabled": False
            }
            url = "https://twitter.com/i/api/graphql/rC2zlE1t7SHbVG8obPZliQ/AudioSpaceById"
        else:
            variables = {
                "id": space_id
            }
            features = {
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "premium_content_api_read_enabled": False,
                "communities_web_enable_tweet_community_results_fetch": True,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
                "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
                "responsive_web_grok_analyze_post_followups_enabled": True,
                "responsive_web_jetfuel_frame": True,
                "responsive_web_grok_share_attachment_enabled": True,
                "articles_preview_enabled": True,
                "payments_enabled": False,
                "profile_label_improvements_pcf_label_in_post_enabled": True,
                "responsive_web_profile_redirect_enabled": False,
                "rweb_tipjar_consumption_enabled": True,
                "verified_phone_label_enabled": False,
                "responsive_web_edit_tweet_api_enabled": True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                "view_counts_everywhere_api_enabled": True,
                "longform_notetweets_consumption_enabled": True,
                "responsive_web_twitter_article_tweet_consumption_enabled": True,
                "tweet_awards_web_tipping_enabled": False,
                "responsive_web_grok_show_grok_translated_post": False,
                "responsive_web_grok_analysis_button_from_backend": True,
                "creator_subscriptions_quote_tweet_preview_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "responsive_web_grok_image_annotation_enabled": True,
                "responsive_web_grok_imagine_annotation_enabled": True,
                "responsive_web_grok_community_note_auto_translation_is_enabled": False,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_enhance_cards_enabled": False
            }
            url = "https://x.com/i/api/graphql/gMKnsAOgD-xxxUgDkJFyAg/BroadcastQuery"

        variables_str = json.dumps(variables)
        features_str = json.dumps(features)
        params = {"variables": variables_str, "features": features_str}

        metadata_response = self.session.get(url, params=params, timeout=10)
        metadata_response.raise_for_status()
        self.metadata = metadata_response.json()
        if 'errors' in self.metadata:
            print(f"Error: {self.metadata['errors'][0]['message']}")
            quit()

    def update_metadata(self, space_id):
        self.get_metadata(space_id)

        if self.type == 'space':
            metadata = self.metadata['data']['audioSpace']['metadata']
            try:
                self.creator = TwitterUser(
                    metadata["creator_results"]["result"]["core"]["name"],
                    metadata["creator_results"]["result"]["core"]["screen_name"],
                    metadata["creator_results"]["result"]["rest_id"]
                    )
            except KeyError:
                self.creator = TwitterUser("Protected_User", "Protected", "0")
            self.title = metadata.get('title') or self.creator.name + "\'s Space"
            self.media_key = metadata["media_key"]
            self.state = metadata["state"]
            self.created_at = metadata["created_at"]
            self.started_at = metadata.get("started_at") or metadata.get('scheduled_start')
            self.updated_at = metadata["updated_at"]
        else:
            metadata = self.metadata['data']['broadcast']
            self.title = metadata.get('status', 'Untitled Broadcast')
            self.media_key = metadata['media_key']
            self.state = metadata['state']
            self.started_at = metadata.get('start_time') or metadata.get('scheduled_start_time')
            try:
                self.creator = TwitterUser(
                    metadata['user_results']["result"]["core"]['name'],
                    metadata['user_results']["result"]["core"]["screen_name"],
                    metadata['user_results']["result"]["rest_id"]
                    )
            except KeyError:
                self.creator = TwitterUser("Protected_User", "Protected", "0")

    def get_chunks(self, playlist_url):
        """
        When we receive the chunks from the server, we want to be able to parse that m3u8 and get all of the chunks from it.

        :param playlists: space playlist url, either master_playlist or playlist_\\d+ (for replay)
        :returns: list of all chunks
        """

        if 'master_' in playlist_url:
            self.debug and print('[DEBUG] fetch sub playlist from master playlist...')
            while True:
                r = self.session.get(playlist_url, timeout=10)
                master_m3u8_obj = m3u8.loads(r.text, uri=playlist_url)
                assert master_m3u8_obj.is_variant, "Expected a master playlist"
                assert len(master_m3u8_obj.playlists) > 0, "No sub-playlists found in the master playlist"
                real_playlist_url = master_m3u8_obj.playlists[-1].absolute_uri
                playlist_name = real_playlist_url.split("/")[-1]
                self.debug and print(f'[DEBUG] current playlist_url is: {playlist_name}')
                r2 = self.session.get(real_playlist_url, timeout=10)
                self.debug and print('[DEBUG] request status code:', r2.status_code)
                if r2.status_code == 200:
                    break
                print(f'[WARN] failed to get {playlist_name} ({r2.status_code}), retry after 10 seconds...')
                time.sleep(10)
        else:
            r2 = self.session.get(playlist_url)
        # Always use playlist_url as the base url instead of the sub-playlist url to get non-transcoding chunks.
        m3u8_obj = m3u8.loads(r2.text, uri=playlist_url)
        chunks = m3u8_obj.segments
        print(f'Get {len(chunks)} chunks.')
        assert len(chunks) > 0, "No chunks found in m3u8"
        return chunks

    def download_chunks(self, chunks, filename, path='.', metadata=None, keep_temp=False):
        """
        Download all of the chunks from the m3u8 to a specified path.

        :param chunks: list of chunks
        :param base_url: the base url of the playlist.
        :param filename: Name of the file we want to write the data to
        :param path: the path to download the chunks to
        :param metadata: any additional metadata that we would like to write to the m4a
        :param keep_temp: keep the temp files
        :returns: None
        """
        path = Path(path)
        chunk_dir = path / ('chunks_' + str(int(datetime.now().timestamp())) + '_' + filename)
        chunk_dir.mkdir()

        def download(chunk_url, key=None, iv=None, chunk_dir=None):
            filename = chunk_url.split("/")[-1]
            f = chunk_dir / filename
            retry_count = 0
            while retry_count < 10:
                if retry_count > 0:
                    print(f"Retry {retry_count} for {filename}...")
                try:
                    with self.session.get(chunk_url, timeout=8) as r:
                        r.raise_for_status()
                        # sometimes the response is "chunked" and doesn't have a content-length header
                        expected_size = int(r.headers.get('Content-Length', -1))
                        bytes_ = r.content
                        actual_size = len(bytes_)
                        if (actual_size == expected_size) or (expected_size == -1 and actual_size > 0):
                            if key is not None and iv is not None:
                                bytes_ = decode(bytes_, key, iv)
                            with f.open("wb") as fio:
                                fio.write(bytes_)
                            break
                        else:
                            print(f"[WARN] Size mismatch: expected {expected_size}, got {actual_size}")
                            retry_count += 1
                except Exception as e:
                    print(f"\nError downloading chunk: {e}")
                    retry_count += 1
            else:
                raise Exception(f"Failed to download chunk {filename} after 10 retries")

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.threads) as ex:
            aes_noted = False
            futures = []
            cached_keys = {}
            for chunk in chunks:
                chunk_url = chunk.absolute_uri
                if key_obj := hasattr(chunk, 'keys') and chunk.keys and chunk.keys[0] or hasattr(chunk, 'key') and chunk.key:
                    if not aes_noted:
                        print("[WARN] AES encryption detected. Will decrypt the chunks.")
                        aes_noted = True
                    key_url = key_obj.absolute_uri
                    if key_url in cached_keys:
                        key = cached_keys[key_url]
                    else:
                        key = self.session.get(key_url).content
                        self.debug and print(f'[DEBUG] add key for {key_url} to cache: {key.hex()}')
                        cached_keys[key_url] = key
                    iv = bytes.fromhex(key_obj.iv[2:])
                else:
                    key, iv = None, None
                futures.append(ex.submit(download, chunk_url, key, iv, chunk_dir))
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
        for chunk in chunks:
            f = chunk_dir / chunk.uri
            assert f.exists(), f"Chunk {f.name} does not exist!"
            files.append(f)

        if keep_temp:
            # generate a list of files
            s = '\n'.join([f.name for f in files])
            Path('chunks_debug.txt').write_text(s, encoding='utf-8')

        self.media_type == 'video' if files[0].suffix == '.ts' else 'audio'
        if self.media_type == 'video':
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
                if metadata is not None:
                    title = metadata["title"]
                    author = metadata["author"]
                    command += f"-metadata title=\"{title}\" -metadata artist=\"{author}\" "
                command += f"\"{output}\""
                self.debug and print(f'[DEBUG] command is {command}')
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
        USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
        assert guest_token is not None or cookies is not None, 'guest_token or cookies must be provided.'
        if guest_token:
            self.session.headers.update({
                "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
                "x-guest-token": guest_token,
                'user-agent': USER_AGENT,
            })
        else:
            cookie_header = "; ".join([f"{name}={value}" for name, value in cookies.items()])
            self.session.headers.update({
                "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
                "x-csrf-token": cookies['ct0'],
                "cookie": cookie_header,
                'user-agent': USER_AGENT,
            })

    def generate_filename(self):
        '''
        Filename Format Options:
        {host_display_name} Host Display Name
        {host_username}     Host Username
        {host_user_id}      Host User ID
        {space_title}       Space Title
        {space_id}          Space ID
        {datetime}          Space Start Time (Local)
        {datetimeutc}       Space Start Time (UTC)
        {type}              Type of the livestream (space or broadcast)
        '''

        if self.given_filename:
            self.filename = safeify(self.given_filename)
            return
        old_filename = self.filename
        if self.filename_format is not None and self.metadata is not None:
            substitutes = dict(
                host_display_name=self.creator.name,
                host_username=self.creator.screen_name,
                host_user_id=self.creator.id,
                space_title=self.title,
                space_id=self.space_id,
                datetime=datetime.fromtimestamp(self.started_at/1000.0),
                datetimeutc=datetime.fromtimestamp(self.started_at/1000.0, tz=timezone.utc),
                type=self.type
            )
            self.filename = self.filename_format.format(**substitutes)
            self.filename = safeify(self.filename)
        else:
            self.filename = f'twitter_{self.type}_' + datetime.now().strftime('%Y%m%d_%H%M%S')
        if old_filename is not None and self.filename != old_filename:
            print(f"Filename updated to: {self.filename}")

    def __init__(self, url_or_space_id=None, dyn_url=None, filename=None, filename_format=None, path=None,
                 with_chat=False, keep_temp=False, cookies=None, type_='space', simulate=False, threads=20, debug=False):
        self.space_id = None
        self.dyn_url = dyn_url
        self.playlist_url = None
        self.chat_token = None
        self.given_filename = filename
        self.filename = None
        self.filename_format = filename_format
        self.path = path
        self.metadata = None
        self.playlists = None
        self.was_running = False
        self.keep_temp = keep_temp
        self.cookies = cookies
        self.type = type_
        self.media_type = None
        self.threads = threads
        self.debug = debug

        self.session = requests_retry_session()

        # set space id and type (if URL given) inplace
        if url_or_space_id:
            self.parse_url_or_space_id(url_or_space_id)
        # if space is is given, we can try to retrieve the metadata.
        if self.space_id is not None:
            if self.cookies is None:
                guest_token = self.get_guest_token()
                self.set_headers(guest_token=guest_token)
            else:
                cookies = load_cookie(self.cookies)
                self.set_headers(cookies=cookies)
            self.update_metadata(self.space_id)

            # if the space is scheduled, wait for it to start
            try:
                while self.state == 'NotStarted':
                    time_to_start = datetime.fromtimestamp(self.started_at/1000.0) - datetime.now()
                    print(f"Waiting for space to start (in {time_to_start})...")
                    time.sleep(10)
                    self.update_metadata(self.space_id)
            except KeyboardInterrupt:
                print("\nAborted by user.")
                return
            try:
                self.playlist_url, self.chat_token = self.get_playlist(self.media_key)
            except:
                print("[WARN] failed to get playlist url and chat token from metadata. If no playlist url is provided, the program will exit.")
        # this is when the user provides a dynamic url
        # it can be used to override the playlist URL given from media_key
        if self.dyn_url:
            self.playlist_url = self.dyn_url
            # try to decide the type only if the space_id is not provided;
            # because the type should have already been confirmed in the previous step otherwise.
            if not self.space_id:
                self.type = 'space' if '/audio-space/' in self.dyn_url else 'broadcast'

        if not self.playlist_url:
            raise ValueError("No playlist URL fetched or provided. Please check your input.")

        # Space now could be video or audio so set the media type based on the playlist url.
        self.media_type = 'audio' if '/audio-space/' in self.playlist_url else 'video'
        self.debug and print('[DEBUG] unmodified raw playlist_url:', self.playlist_url)

        # fetch the static master playlist, if the input isn't a sub-playlist already.
        # Remove prefix such as https://twitter.com/i/live_video_stream/authorized_status/1618183355492859905/LIVE_PUBLIC/FnTxMDWaAAE_38D?url=https://prod-ec-ap-northeast-1.video.pscp.tv/...
        self.playlist_url = re.sub(r"https?://(www\.)?(twitter|x)\.com/.+?\?url=", "", self.playlist_url)

        base, name = self.playlist_url.rsplit('/', 1)
        # get prefix, if any
        if name.split('_')[0] not in ['master', 'playlist', 'dynamic']:
            prefix = name.split('_')[0] + '_'
        else:
            prefix = ''
        if m := re.search(r'(master_)?(dynamic_)?(playlist_)?(?P<timestamp>\d+)\.m3u8(\?.+)?', name):
            self.playlist_url = f'{base}/{prefix}playlist_{m["timestamp"]}.m3u8'
        else:
            self.playlist_url = f'{base}/{prefix}master_playlist.m3u8'

        # Replace transcode url with non-transcode url
        # from /transcode/{server_region}/{server_deploy}/{transcode_settings}/
        # to /non_transcode/{server_region}/{server_deploy}/
        self.playlist_url = re.sub(r'/transcode/([^/]+/[^/]+/)[^/]+/', r'/non_transcode/\1', self.playlist_url)

        self.generate_filename()
        # NOT TESTED
        # Now start a subprocess for running the chat exporter
        if with_chat == True and self.type == 'space':
            if self.chat_token is None:
                print('[ChatExporter] Chat Token is None. Chat Exporting will not be performed.')
            else:
                print("[ChatExporter] Chat Exporting is currently only supported for Ended Spaces with a recording. To Export Chat for a live space, copy the chat token and use WebSocketDriver.py.")
                chatThread = Thread(target=WebSocketHandler.SpaceChat, args=(self.chat_token, self.filename, self.path,))
            #chatThread.start()

        m4a_metadata = None
        if self.metadata is not None:
            # Print out the space/broadcast information
            type_name = self.type.capitalize()
            suffix = '.ts' if self.media_type == 'video' else '.m4a'
            print(f"{type_name} Found!")
            print(f"{type_name} ID: {self.space_id}")
            print(f"{type_name} Type: {self.media_type}")
            print(f"{type_name} Title: {self.title}")
            print(f'{type_name} Current State: {self.state}')
            print(f"{type_name} Host Username: {self.creator.screen_name}")
            print(f"{type_name} Host Display Name: {self.creator.name}")
            print(f"{type_name} Playlist URL:\n{self.playlist_url}")
            print(f"Chat Token:\n{self.chat_token}")
            print(f"Downloading to {self.filename}{suffix}")
            m4a_metadata = {"title" : self.title, "author" : self.creator.screen_name}

            if self.state == "Running":
                self.was_running = True # this is only useful for chat exporter
                print("Waiting for space to end...")
                while self.state == "Running":
                    try:
                        #TODO: live download
                        self.update_metadata(self.space_id)
                        self.generate_filename() # update filename if the space title changes
                        time.sleep(10)
                    except Exception:
                        self.state = "ERROR"
                print("Space Ended. Wait 1 minute for the recording to be processed.")
                time.sleep(60)

        chunks = self.get_chunks(self.playlist_url)
        if simulate:
            print("Simulate mode, no download will be performed.")
            return
        self.download_chunks(chunks, self.filename, self.path, m4a_metadata, keep_temp=self.keep_temp)

        if with_chat == True and self.chat_token is not None and self.state == "Ended" and self.was_running == False:
            chatThread.start() # If We're Downloading a Recording, we're all good to download the chat.
            print("[ChatExporter]: Chat Thread Started")
