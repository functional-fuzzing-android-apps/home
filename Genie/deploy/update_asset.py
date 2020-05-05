from argparse import ArgumentParser, Namespace
from functools import partial
from pathlib import Path
from subprocess import run

import pkg_resources

from .logger import get_logger
from .start import Test

logger = get_logger('updater')


def update_test(t: Test, cla: Namespace) -> Test:
    logger.info('updating {}'.format(t))
    return t


if __name__ == '__main__':
    ap = ArgumentParser()

    ap.add_argument('output', metavar='output-dir')

    args = ap.parse_args()

    update = partial(update_test, cla=args)

    output = Path(args.output)

    for seed in update(output).glob('seed-tests/seed-test-*'):
        for mutant in update(seed).glob('mutant-*'):
            update(mutant)
