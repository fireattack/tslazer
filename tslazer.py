# tslazer.py
# author: ef1500
import os
import argparse
import TwitterSpace

parser = argparse.ArgumentParser(description="Download Twitter Spaces at lazer fast speeds!", formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("--path", "-p", type=str, default='.', help="Path to download the space")
parser.add_argument("--keep", "-k", action='store_true', help="Keep the temporary files")

spaceID_group = parser.add_argument_group("Downloading from a Space ID/URL")
spaceID_group.add_argument("--space_id", "-s", type=str, help="Twitter Space ID or URL")
spaceID_group.add_argument("--withchat", "-c", action='store_true', help="Export the Twitter Space's Chat")

filenameformat_default = "{datetime:%y%m%d} @{host_username} {space_title}-twitter-space-{space_id}"

fileformat_options = """
    {host_display_name}	Host Display Name
    {host_username}     Host Username
    {host_user_id}      Host User ID
    {space_title}       Space Title
    {space_id}          Space ID
    {datetime}          Datetime (Local)
    {datetimeutc}       Datetime (UTC)
Default: """ + filenameformat_default.replace("%", "%%")
spaceID_group.add_argument("--filenameformat", "-f", default=filenameformat_default, type=str, help=f"File Format Options: {fileformat_options}")

dyn_group = parser.add_argument_group("Downloading from a dynamic or master URL")
dyn_group.add_argument("--dyn_url", "-d", type=str, help="Twitter Space Master URL or Dynamic Playlist URL")
dyn_group.add_argument("--filename", "-o", default="", type=str, help="Filename for the Twitter Space")
args = parser.parse_args()

if args.space_id != None and args.filenameformat != None:
    TwitterSpace.TwitterSpace(space_id=args.space_id, filenameformat=args.filenameformat, path=args.path, withChat=args.withchat, keep_temp=args.keep)
if args.dyn_url != None and args.filename != None:
    TwitterSpace.TwitterSpace(dyn_url=args.dyn_url, filename=args.filename, path=args.path, keep_temp=args.keep)
