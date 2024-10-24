import argparse
import TwitterSpace


parser = argparse.ArgumentParser(description="Download Twitter Spaces at lazer fast speeds!", formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("--path", "-p", default='.', help="Path to download the space")
parser.add_argument("--keep", "-k", action='store_true', help="Keep the temporary files")
parser.add_argument("--cookies", "--cookie", "-c", help="Twitter cookies.txt file (in Netscape format)")
parser.add_argument("--threads", "-t", type=int, default=20, help="Number of threads to use for downloading")
parser.add_argument("--simulate", "-S", action='store_true', help="Simulate the download process")
parser.add_argument("--debug", action='store_true', help="Enable debug logging. Will be automatically enabled if --simulate is used")

spaceID_group = parser.add_argument_group("Downloading from a Space/Broadcast ID/URL")
spaceID_group.add_argument("--space_id", "-s", help="Twitter Space/Broadcast ID or URL")
spaceID_group.add_argument("--video", "--broadcast", "-v", "-b", action='store_true', help="Assume type is broadcast (instead of space) when only the ID is given. It is auto inferred if the full URL is given.")
spaceID_group.add_argument("--withchat", action='store_true', help="Export the Twitter Space's Chat")

filenameformat_default = "{datetime:%y%m%d} @{host_username} {space_title}-twitter-{type}-{space_id}"
fileformat_options = """
    {host_display_name}	Host Display Name
    {host_username}     Host Username
    {host_user_id}      Host User ID
    {space_title}       Space/Broadcast Title
    {space_id}          Space/Broadcast ID
    {datetime}          Space/Broadcast Start Time (Local)
    {datetimeutc}       Space/Broadcast Start Time (UTC)
    {type}              Type of the livestream (space or broadcast)
Default: """ + filenameformat_default.replace("%", "%%")
spaceID_group.add_argument("--filenameformat", "-f", default=filenameformat_default, help=f"File Format Options: {fileformat_options}")

dyn_group = parser.add_argument_group("Downloading from a dynamic or master URL")
dyn_group.add_argument("--dyn_url", "-d", help="Twitter Space Master URL or Dynamic Playlist URL")
dyn_group.add_argument("--filename", "-o", help="Filename for the Twitter Space (default: twitter_{type}_{current_time:%%Y%%m%%d_%%H%%M%%S})")
args = parser.parse_args()

TwitterSpace.TwitterSpace(
    url_or_space_id=args.space_id, filenameformat=args.filenameformat,
    dyn_url=args.dyn_url, filename=args.filename,
    path=args.path, with_chat=args.withchat, keep_temp=args.keep,
    cookies=args.cookies, simulate=args.simulate,
    type_="broadcast" if args.video else "space", threads=args.threads,
    debug=args.debug or args.simulate
)
