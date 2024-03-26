### Tslazer-lite

**IMPORTANT: Since June/July 2023, you can no longer download Twitter Spaces from a Space ID without logging in. Make sure to feed in `cookies.txt` to the program using `--cookies` argument. You can still download directly from Master/Dynamic URL without cookies.**

This is an almost-rewrite based on original [Tslazer v1](https://github.com/HoloArchivists/tslazer) (not the overhaul branch). The codebase is largely rewritten and refactored to be more readable and maintainable. The main goal is to make it easier to understand and modify the code.

Functionality wise, it is mostly the same as the original, with some QoL changes and improvements.

Some significant changes:
- Filename format (and filename if using dyn_url directly) now has a sensible default. So you don't need to always specify it.
- Changed filename format templating to use python's [string formatting](https://docs.python.org/3/library/string.html#format-string-syntax) instead of custom templating. This allows for more flexibility and less code. For example, you can now use `{datetime:%y%m%d}` to get the date in `yymmdd` format.
- Added retry for all the requests. This is to prevent the program from crashing when the connection is unstable.
- When merging raw AACs (ADTS), it now uses binary concatenation instead of ffmpeg concat filter. This is to work around a bug in ffmpeg concat that causes the audio to be having wrong duration. See [this thread](https://www.reddit.com/r/ffmpeg/comments/13pds8a/why_does_concatenate_raw_aac_files_directly_into/) I created on Reddit for more info. It will still be converted to MP4 by ffmpeg in the end.

#### Usage

|  Supported URL Sources | Example|
| :------------: | -------------- |
| Space ID/URL | `tslazer -s 1ZkJzbdvLgyJv -c cookies.txt` |
| Master/Dynamic URL| `tslazer -d DYN_URL` |

### Requirements
This program requires `ffmpeg` binary to work. Make sure you have one in your `PATH`.

#### Arguments
    usage: tslazer.py [-h] [--path PATH] [--keep] [--cookies COOKIES] [--space_id SPACE_ID] [--withchat] [--filenameformat FILENAMEFORMAT] [--dyn_url DYN_URL] [--filename FILENAME]

    Download Twitter Spaces at lazer fast speeds!

    options:
      -h, --help            show this help message and exit
      --path PATH, -p PATH  Path to download the space
      --keep, -k            Keep the temporary files
      --cookies COOKIES, --cookie COOKIES, -c COOKIES
                            Twitter cookies.txt file (in Netscape format)

    Downloading from a Space ID/URL:
      --space_id SPACE_ID, -s SPACE_ID
                            Twitter Space ID or URL
      --withchat            Export the Twitter Space's Chat
      --filenameformat FILENAMEFORMAT, -f FILENAMEFORMAT
                            File Format Options:
                                {host_display_name} Host Display Name
                                {host_username}     Host Username
                                {host_user_id}      Host User ID
                                {space_title}       Space Title
                                {space_id}          Space ID
                                {datetime}          Space Start Time (Local)
                                {datetimeutc}       Space Start Time (UTC)
                            Default: {datetime:%y%m%d} @{host_username} {space_title}-twitter-space-{space_id}

    Downloading from a dynamic or master URL:
      --dyn_url DYN_URL, -d DYN_URL
                            Twitter Space Master URL or Dynamic Playlist URL
      --filename FILENAME, -o FILENAME
                            Filename for the Twitter Space (default: twitter_space_{current_time:%Y%m%d_%H%M%S})

|  Argument  |  Description |
| ------------ | ------------ |
| space_id | The Url or id of a Twitter Space. |
| filenameformat | The filename format for the space. See the help above for more info. |
| dyn_url | Master URL of a Twitter Space. Ends with `dynamic_playlist.m3u8` or `master_playlist.m3u8` |
| filename | The filename for the space. There is no need  to specify a file extension, as this is done automatically for you |
| path | The path to download the space to. |
| keep | Keep all the temporary files. Useful for debugging or when ffmpeg failed to convert the audio. |