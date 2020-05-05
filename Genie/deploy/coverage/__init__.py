# Ref: https://www.eclemma.org/jacoco/trunk/doc/cli.html
from os.path import dirname, join, abspath
from subprocess import run
from typing import List

from ..logger import get_logger

logger = get_logger('coverage')

jacoco_jar = join(dirname(dirname(dirname(abspath(__file__)))),
                  'droidbot/resources/jacococli.jar')


def merge(output: str, inputs: List[str]):
    _inputs = []
    if len(inputs) > 1000:
        for bucket_i in range((len(inputs) // 1000) + 1):
            output_i = '{}_{}'.format(output, bucket_i)
            _inputs.append(output_i)

            merge(output_i, inputs[1000 * bucket_i:1000 * (bucket_i + 1)])

        inputs = _inputs

    run(['java', '-jar', jacoco_jar, 'merge'] + inputs + ['--destfile', str(output)])

    for _i in _inputs:
        run(['rm', '-rf', _i])
