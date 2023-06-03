from util import requests_retry_session
import re
from urllib.parse import urlparse
from TwitterSpace import TwitterSpace
from rich import print



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


master_url = "https://prod-fastly-ap-northeast-1.video.pscp.tv/Transcoding/v1/hls/pxBnReI2LcTHLle-LVyb2qcazCAsPsAz1RjTGdm1WjIP3-dduSt965Bh7gp2JvjfTpheVRcPOFOaZeDnsKEXTw/non_transcode/ap-northeast-1/periscope-replay-direct-prod-ap-northeast-1-public/audio-space/master_playlist.m3u8"

playlists = getPlaylists(dyn_url=master_url)
print(playlists.__dict__)