from pathlib import Path
from typing import Union


def init_logger():
    import logging

    r = logging.getLogger()

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    ch.setFormatter(formatter)
    r.addHandler(ch)


def set_log_file(file: Union[str, Path]):
    import logging

    fh = logging.FileHandler(file)
    fh.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    fh.setFormatter(formatter)
    logging.getLogger().addHandler(fh)

    logging.info('{} as DEBUG log file'.format(file))


def get_logger(name='__main__'):
    if name == '__main__':
        name = 'main'
    from logging import getLogger, DEBUG
    r = getLogger(name)
    r.setLevel(DEBUG)
    return r
