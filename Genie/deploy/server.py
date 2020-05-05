import os
import sys
import urllib.parse
from argparse import ArgumentParser
from functools import partial
from http import HTTPStatus
from http.server import test, SimpleHTTPRequestHandler


class ListDirHTTPRequestHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        """
        Do not automatically return index.html
        :return:
        """
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                new_parts = (parts[0], parts[1], parts[2] + '/',
                             parts[3], parts[4])
                new_url = urllib.parse.urlunsplit(new_parts)
                self.send_header("Location", new_url)
                self.end_headers()
                return None
            return self.list_directory(path)
        return super().send_head()


if __name__ == '__main__':
    ap = ArgumentParser()

    ap.add_argument('--port', default=80, type=int)
    ap.add_argument('dir', action='store', nargs='?', default=os.getcwd())

    args = ap.parse_args()

    if sys.version_info < (3, 7, 0):
        os.chdir(args.dir)
        test(ListDirHTTPRequestHandler, port=args.port)
    else:
        test(partial(ListDirHTTPRequestHandler, directory=args.dir), port=args.port)
