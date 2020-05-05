from argparse import ArgumentParser

from . import merge

if __name__ == '__main__':
    ap = ArgumentParser(description="Merge single coverage files")

    ap.add_argument('--output', required=True)

    ap.add_argument('file', nargs='+')

    args = ap.parse_args()

    merge(args.output, args.file)
