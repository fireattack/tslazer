### Tslazer-lite

***Twitter Space and Broadcast (pscp.tv) Downloader***

**IMPORTANT: Since Oct 2024, downloading from a Space/Broadcast ID without logging is working again. But it is still recommended to use cookies to prevent limiting in future.**

This is an almost-rewrite based on original [Tslazer v1](https://github.com/HoloArchivists/tslazer) (not the overhaul branch). The codebase is largely rewritten and refactored to be more readable and maintainable. The main goal is to make it easier to understand and modify the code.

Some significant changes:
- Filename format (and filename if using dyn_url directly) now has a sensible default. So you don't need to always specify it.
- Changed filename format templating to use python's [string formatting](https://docs.python.org/3/library/string.html#format-string-syntax) instead of custom templating. This allows for more flexibility and less code. For example, you can now use `{datetime:%y%m%d}` to get the date in `yymmdd` format.
- Added retry for all the requests. This is to prevent the program from crashing when the connection is unstable.
- When merging raw AACs (ADTS), it now uses binary concatenation instead of ffmpeg concat filter. This is to work around a bug in ffmpeg concat that causes the audio to be having wrong duration. See [this thread](https://www.reddit.com/r/ffmpeg/comments/13pds8a/why_does_concatenate_raw_aac_files_directly_into/) I created on Reddit for more info. It will still be converted to MP4 by ffmpeg in the end.
- For videos, it downloads the original non-transcoded chunks to get the best quality.

#### Usage

|  Supported URL Sources | Example|
| :------------: | -------------- |
| Space ID/URL | `tslazer -s 1ZkJzbdvLgyJv -c cookies.txt` |
| Master/Dynamic URL| `tslazer -d DYN_URL` |

### Requirements
This program requires `ffmpeg` binary to work. Make sure you have one in your `PATH`.

#### Arguments
    usage: tslazer.py [-h] [--path PATH] [--keep] [--cookies COOKIES] [-t THREADS] [--simulate] [--space_id SPACE_ID] [-v] [--withchat] [--filenameformat FILENAMEFORMAT] [--dyn_url DYN_URL] [--filename FILENAME]

    Download Twitter Spaces at lazer fast speeds!

    options:
      -h, --help            show this help message and exit
      --path PATH, -p PATH  Path to download the space
      --keep, -k            Keep the temporary files
      --cookies COOKIES, --cookie COOKIES, -c COOKIES
                            Twitter cookies.txt file (in Netscape format)
      -t THREADS, --threads THREADS
                            Number of threads to use for downloading
      --simulate, -S        Simulate the download process

    Downloading from a Space/Broadcast ID/URL:
      --space_id SPACE_ID, -s SPACE_ID
                            Twitter Space/Broadcast ID or URL
      -v, --video           Assume type is video when only the ID is given. It is auto inferred if the full URL is given.
      --withchat            Export the Twitter Space's Chat
      --filenameformat FILENAMEFORMAT, -f FILENAMEFORMAT
                            File Format Options:
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