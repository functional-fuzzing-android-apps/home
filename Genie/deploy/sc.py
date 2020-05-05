"""
Take screenshot
"""
from argparse import ArgumentParser
from io import BytesIO
from logging import getLogger
from subprocess import run, DEVNULL, PIPE, TimeoutExpired
from typing import Optional

from PIL import Image

from .utils import timeout_run


def take_sc(device: str, timeout=10) -> Optional[Image.Image]:
    try:
        _cmd = ['adb', '-s', device, 'shell', 'screencap', '-p']
        _p = timeout_run(_cmd, stdout=PIPE, stderr=DEVNULL, timeout=timeout)
        if _p.returncode != 0:
            getLogger().warning('`{}` return {}'.format(' '.join(_cmd), _p.returncode))
            return None
        received = _p.stdout.replace(b'\r\n', b'\n')
    except TimeoutExpired:
        getLogger().warning('get sc from {} timeout after {} seconds'.format(device, timeout))
        return None
    stream = BytesIO(received)

    try:
        image = Image.open(stream)
    except IOError as e:
        # getLogger().exception(e)
        getLogger().warning('error loading sc from {}'.format(device))
        return None
    return image


if __name__ == '__main__':
    ap = ArgumentParser()

    ap.add_argument('device', type=str)
    ap.add_argument('--out', default='out.png')

    args = ap.parse_args()

    _sc = take_sc(args.device)
    _sc.save(args.out)
