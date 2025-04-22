from http.cookiejar import MozillaCookieJar
from pathlib import Path
from shutil import copyfileobj

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Modified from https://www.peterbe.com/plog/best-practice-with-retries-with-requests
def requests_retry_session(
    retries=3,
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
    for i, f in enumerate(files):
        f = Path(f)
        fi = f.open('rb')
        copyfileobj(fi, out)
        fi.close()
        print(f'\r{i + 1}/{len(files)} chunks merged.      ', end='')
    out.close()
    print()

def load_cookie(filename):
    cj = MozillaCookieJar(filename)
    cj.load(ignore_expires=True, ignore_discard=True)
    return {cookie.name: cookie.value for cookie in cj}


def decode(bytes_, key, iv):
    """Decrypt a file using AES CBC with the provided key and IV.
    Args:
        bytes_ (bytes): The encrypted data to decrypt.
        key (bytes): The AES key used for decryption.
        iv (bytes): The initialization vector used for decryption.
    Returns:
        bytes: The decrypted data.
    """
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    return unpad(cipher.decrypt(bytes_), AES.block_size)