import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pathlib import Path
from shutil import copyfileobj

# Modified from https://www.peterbe.com/plog/best-practice-with-retries-with-requests
def requests_retry_session(
    retries=5,
    backoff_factor=0.2,
    status_forcelist=None, # (500, 502, 504)
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def safeify(name, ignore_backslash=False):
    template = {'\\': '＼', '/': '／', ':': '：', '*': '＊', '?': '？', '"': '＂', '<': '＜', '>': '＞', '|': '｜','\n':'','\r':'','\t':''}
    if ignore_backslash:
        template.pop('\\', None)

    for illegal in template:
        name = name.replace(illegal, template[illegal])
    return name

def concat(files, output):
    output = Path(output)
    if not output.parent.exists():
        output.parent.mkdir(parents=True)
    out = output.open('wb')
    for f in files:
        f = Path(f)
        fi = f.open('rb')
        copyfileobj(fi, out)
        fi.close()
    out.close()
