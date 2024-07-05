## Livestreams

when fetching from a live space, the url returned by the API looks like this:

    https://prod-fastly-ap-northeast-1.video.pscp.tv/Transcoding/v1/hls/{somehash}/non_transcode/ap-northeast-1/periscope-replay-direct-prod-ap-northeast-1-public/audio-space/dynamic_playlist.m3u8?type=live

This is a dynamic (live) playlist directly links to the chunks:

    #EXTM3U
    #EXT-X-VERSION:6
    #EXT-X-TARGETDURATION:4
    #EXT-X-INDEPENDENT-SEGMENTS
    #EXT-X-MEDIA-SEQUENCE:1704
    #EXT-X-DISCONTINUITY-SEQUENCE:0
    #EXT-X-START:TIME-OFFSET=0.01
    #EXT-X-PROGRAM-DATE-TIME:2024-07-05T15:17:40.257Z
    #EXTINF:3.008,
    chunk_1720192654637762497_1704_a.aac?type=live
    #EXT-X-PROGRAM-DATE-TIME:2024-07-05T15:17:43.280Z
    #EXTINF:2.987,
    chunk_1720192657533692001_1705_a.aac?type=live
    #EXT-X-PROGRAM-DATE-TIME:2024-07-05T15:17:46.274Z
    #EXTINF:3.008,
    chunk_1720192660621786722_1706_a.aac?type=live
    #EXT-X-PROGRAM-DATE-TIME:2024-07-05T15:17:49.264Z
    #EXTINF:3.008,
    chunk_1720192663620883094_1707_a.aac?type=live

so you can get the newest chunks by refreshing this playlist.

To get existing chunks, though, you need to get the master playlist first, then get the sub playlist, then get the chunks, because the playlist(s) have a timestamp suffix in filename.

Firstly, replace `/dynamic_playlist.m3u8?type=live` with `/master_playlist.m3u8` (do NOT keep the `?type=live` query string):

    https://prod-fastly-ap-northeast-1.video.pscp.tv/Transcoding/v1/hls/{somehash}/non_transcode/ap-northeast-1/periscope-replay-direct-prod-ap-northeast-1-public/audio-space/master_playlist.m3u8

This is a static (end list) master m3u8 playlists which has multiple sub-playlists with a timestamp, e.g.

    https://prod-fastly-ap-northeast-1.video.pscp.tv/Transcoding/v1/hls/{somehash}/transcode/ap-northeast-1/periscope-replay-direct-prod-ap-northeast-1-public/{transcoding settings in JWT}/audio-space/playlist_16761019244202992663.m3u8

(Sometimes the sub playlist is 404, you need to wait for awhile and try again.)

These sub playlists are also static (end list); but the master list would refresh and give you the new ones (with new timestamp), just not very often.

Typically, we only fetch the master playlist after the live ends + 1 minute, to make sure our sub playlist contains all the chunks.

To get chunks, simply fetch the content of this sub-playlist. But to get the best quality, you should join the chunk path with the base URL of the master playlist (`/non_transcode/`) to get the original, non-transcoded chunks.

For live (video) broadcast, the url returned by the API looks like this:

    https://prod-ec-ap-northeast-1.video.pscp.tv/Transcoding/v1/hls/et7l8-1w_IfKg_2avCodsJLiUONtwHkogQMIJ920sFyfwtPrPtJnBqIn-P6yxAjpWMv6G9Thry5RolyE58kQLg/non_transcode/ap-northeast-1/periscope-replay-direct-prod-ap-northeast-1-public/master_dynamic_playlist.m3u8?type=live

which would have various /transcode/ sub-playlists like:

    /Transcoding/v1/hls/et7l8-1w_IfKg_2avCodsJLiUONtwHkogQMIJ920sFyfwtPrPtJnBqIn-P6yxAjpWMv6G9Thry5RolyE58kQLg/transcode/ap-northeast-1/periscope-replay-direct-prod-ap-northeast-1-public/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsInZlcnNpb24iOiIyIn0.eyJFbmNvZGVyU2V0dGluZyI6ImVuY29kZXJfc2V0dGluZ183MjBwMzBfMTAiLCJIZWlnaHQiOjcyMCwiS2JwcyI6Mjc1MCwiV2lkdGgiOjEyODB9.ldktM4fCFRfkP4ZEBfZPKtlAUNAcTPkoz994YJAzWpE/dynamic_playlist.m3u8?type=live

At this point I don't know if there would be `/non_transcode/` `/dynamic_playlist.m3u8?type=live` file so you can directly get newest chunks; but it doesn't matter since we can always get the chunk names from the sub-playlists.

## Recordings

when fetching from a recording, it usually directly returns you the `non_transcode`, (sub-)playlist, e.g.:

    https://prod-fastly-ap-northeast-1.video.pscp.tv/Transcoding/v1/hls/{somehash}/non_transcode/ap-northeast-1/periscope-replay-direct-prod-ap-northeast-1-public/audio-space/playlist_16760776723829618751.m3u8?type=replay

So you can just use this URL to get the chunks.

For broadcast (video) recordings, the URL returned by API is:

    https://prod-ec-ap-northeast-1.video.pscp.tv/Transcoding/v1/hls/{somehash}/non_transcode/ap-northeast-1/periscope-replay-direct-prod-ap-northeast-1-public/master_dynamic_16726907818458204116.m3u8?type=replay

which has sub-playlists like:

    /Transcoding/v1/hls/{somehash}/transcode/ap-northeast-1/periscope-replay-direct-prod-ap-northeast-1-public/{transcoding settings in JWT}/playlist_16726907818458204116.m3u8?type=replay

Again, you can use similar tricks to get chunk paths from it and join them with `/non_transcode/` base to get the original chunks. In this case, you can even just replace the m3u8 from `master_dynamic_` to `playlist_` to get the original chunks directly.