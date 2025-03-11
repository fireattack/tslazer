## Tslazer-lite
***Twitter Space and Broadcast (pscp.tv) Downloader***

**IMPORTANT: Since Oct 2024, downloading from a Space/Broadcast ID without logging in is working again. But it is still recommended to use cookies to prevent limiting in future.**

This is an almost-rewrite based on original [Tslazer v1](https://github.com/HoloArchivists/tslazer) (not the overhaul branch). The codebase is largely rewritten and refactored to be more readable and maintainable. The main goal is to make it easier to understand and modify the code.

Some significant changes:
- Filename format (and filename if using dyn_url directly) now has a sensible default. So you don't need to always specify it.
- Changed filename format templating to use python's [string formatting](https://docs.python.org/3/library/string.html#format-string-syntax) instead of custom templating. This allows for more flexibility. For example, you can now use `{datetime:%y%m%d}` to get the date in `yymmdd` format.
- Added retry for all the requests.
- When merging raw AACs (ADTS), it now uses binary concatenation instead of ffmpeg concat filter. This is to work around a bug in ffmpeg concat that causes the audio to be having wrong duration. See [this thread](https://www.reddit.com/r/ffmpeg/comments/13pds8a/why_does_concatenate_raw_aac_files_directly_into/) I created on Reddit for more info. It will still be remuxed into MP4 by ffmpeg in the end.
- It always downloads the original non-transcoded chunks to get the best quality (especially for videos).

### Requirements
This program requires `ffmpeg` binary to work. Make sure you have one in your `PATH`.

### Typical command examples
|  Supported Inputs | Example | Note |
| :------------: | -------------- | -------------- |
| Space ID | `tslazer -s 1ZkJzbdvLgyJv` | It is recommanded to use `-c cookies.txt` with it. |
| Broadcast ID | `tslazer -s 1mnxeAVmnYaxX --broadcast` | Use `--broadcast` to indicate it is a broadcast instead of a space. |
| Space/Broadcast URL | `tslazer -s "https://x.com/i/broadcasts/1mnxeAVmnYaxX"` | It will automatically detect if it is a space or broadcast. |
| Master/Dynamic URL| `tslazer -d "https://prod-fastly-ap-northeast-2.video.pscp.tv/Transcoding/....m3u8"` | Any master/dynamic m3u8 URL will work. |
| Space ID and Master/Dynamic URL | `tslazer -s {ID} -d "https://prod-fastly-ap-northeast-2.video.pscp.tv/Transcoding/....m3u8"` | You can use the combination of both for Spaces that are already ended. This way, metadata can be fetched from the Space ID. |

### Detailed Usage
    usage: tslazer.py [-h] [--path PATH] [--keep] [--cookies COOKIES] [--threads THREADS] [--simulate] [--debug] [--space_id SPACE_ID] [--video] [--withchat]
                      [--filename-format FILENAME_FORMAT] [--dyn_url DYN_URL] [--filename FILENAME]

    Download Twitter Spaces at lazer fast speeds!

    options:
      -h, --help            show this help message and exit
      --path PATH, -p PATH  Path to download the space
      --keep, -k            Keep the temporary files
      --cookies COOKIES, --cookie COOKIES, -c COOKIES
                            Twitter cookies.txt file (in Netscape format)
      --threads THREADS, -t THREADS
                            Number of threads to use for downloading
      --simulate, -S        Simulate the download process
      --debug               Enable debug logging. Will be automatically enabled if --simulate is used

    Downloading from a Space/Broadcast ID/URL:
      --space_id SPACE_ID, -s SPACE_ID
                            Twitter Space/Broadcast ID or URL
      --video, --broadcast, -v, -b
                            Assume type is broadcast (instead of space) when only the ID is given. It is auto inferred if the full URL is given.
      --withchat            Export the Twitter Space's Chat
      --filename-format FILENAME_FORMAT, -f FILENAME_FORMAT
                            Filename Format Options:
                                {host_display_name} Host Display Name
                                {host_username}     Host Username
                                {host_user_id}      Host User ID
                                {space_title}       Space/Broadcast Title
                                {space_id}          Space/Broadcast ID
                                {datetime}          Space/Broadcast Start Time (Local)
                                {datetimeutc}       Space/Broadcast Start Time (UTC)
                                {type}              Type of the livestream (space or broadcast)
                            Default: {datetime:%y%m%d} @{host_username} {space_title}-twitter-{type}-{space_id}

    Downloading from a dynamic or master URL:
      --dyn_url DYN_URL, -d DYN_URL
                            Twitter Space Master URL or Dynamic Playlist URL
      --filename FILENAME, -o FILENAME
                            Filename for the Twitter Space (default: twitter_{type}_{current_time:%Y%m%d_%H%M%S})
