### Tslazer-fork
This is a fork of original [Tslazer v1](https://github.com/HoloArchivists/tslazer) (not overhaul branch) with some QoL changes for myself.

Significant changes:
- filename format (and filename if using dyn_url directly) now has a sensible default. So you don't need to always specify it.
- change filename format templating to use python's [string formatting](https://docs.python.org/3/library/string.html#format-string-syntax) instead of custom templating. This allows for more flexibility and less code.
- Add retry for all the requests. This is to prevent the program from crashing when the connection is unstable.
- When merging raw AAC (ADTS), use binary concat instead of ffmpeg concat. This is to work around a bug in ffmpeg concat that causes the audio to be having wrong duration. See [this thread](https://www.reddit.com/r/ffmpeg/comments/13pds8a/why_does_concatenate_raw_aac_files_directly_into/) I created on Reddit for more info. It will still be converted to MP4 by ffmpeg in the end.

See original repo for more info.

#### Usage

|  Supported URL Sources | Example|
| :------------: | -------------- |
| Space ID/URL | `tslazer -s 1ZkJzbdvLgyJv` |
| Master/Dynamic URL| `tslazer -d DYN_URL` |

### Requirements
This program requires `ffmpeg` to work. You can install it using `sudo apt install ffmpeg`.

#### Arguments

    usage: tslazer.py [-h] [--path PATH] [--space_id SPACE_ID] [--withchat] [--filenameformat FILENAMEFORMAT] [--dyn_url DYN_URL] [--filename FILENAME]

    Download Twitter Spaces at lazer fast speeds!

    options:
      -h, --help            show this help message and exit
      --path PATH, -p PATH  Path to download the space

    Downloading from a Space ID/URL:
      --space_id SPACE_ID, -s SPACE_ID
                            Twitter Space ID or URL
      --withchat, -c        Export the Twitter Space's Chat
      --filenameformat FILENAMEFORMAT, -f FILENAMEFORMAT
                            File Format Options:
                                {host_display_name} Host Display Name
                                {host_username}     Host Username
                                {host_user_id}      Host User ID
                                {space_title}       Space Title
                                {space_id}          Space ID
                                {datetime}          Datetime (Local)
                                {datetimeutc}       Datetime (UTC)
                            Default: {datetime:%y%m%d} @{host_username} {space_title}-twitter-space-{space_id}

    Downloading from a dynamic or master URL:
      --dyn_url DYN_URL, -d DYN_URL
                            Twitter Space Master URL or Dynamic Playlist URL
      --filename FILENAME, -fn FILENAME
                            Filename for the Twitter Space


|  Argument  |  Description |
| ------------ | ------------ |
| filename | The filename for the space. There is no need  to specify a file extension, as this is done automatically for you |
| dyn_url | Master URL of a Twitter Space. Ends with `dynamic_playlist.m3u8` or `master_playlist.m3u8` |
| space_id | The Url or id of a Twitter Space. |