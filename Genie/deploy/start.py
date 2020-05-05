"""
Start AVD and run tests.
"""
import json
from atexit import register
from functools import lru_cache
from json import loads
from argparse import ArgumentParser, Namespace
from logging import Logger
from multiprocessing import Process, Value
from pathlib import Path
from re import search, match
from subprocess import TimeoutExpired, PIPE, Popen
from threading import Thread
from time import sleep, time
from typing import List, Optional, Callable, Any, Union, Dict, Tuple

from .trie import SeqTrie
from .logger import get_logger, set_log_file, init_logger
from .emulator import wait_ready, emulator_process, ith_emulator_name
from .utils import timeout_run, list_devices, debug_assert, time_str
from .sc import take_sc

main_logger = get_logger(__name__)

"""use Path to represent a test case"""
Test = Path
RunHistory = List[Test]

# '<seed_id>-<mutant_id>'
TestHash = str

trie_tree: Optional[SeqTrie] = None

RESTART_AFTER_MUTANTS = 0
RESTART_AFTER_SECONDS = 0


def trie_update(mutant: Test):
    global trie_tree
    if trie_tree is None:
        return

    gui_check_output = mutant / 'checking_result.json'
    if not gui_check_output.exists():
        main_logger.warning('{} not exist, do not update trie tree'.format(gui_check_output))
        return

    checking_result_json_file = open(str(gui_check_output), "r")
    checking_result_dict = json.load(checking_result_json_file)
    checking_result_json_file.close()

    if checking_result_dict['is_fully_replayed']:
        main_logger.debug('{} is replayable, do not update trie'.format(mutant))
        return

    ids = checking_result_dict['unreplayable_utg_event_ids_prefix']
    trie_tree.update(ids)


def trie_check_valid(mutant: Test, log=False, invalid_callback: Optional[Callable[[Test, Any], None]] = None) -> bool:
    """
    Return if this sequence is valid with given trie model
    """
    global trie_tree
    if trie_tree is None:
        return True
    utg_json = mutant / 'utg.json'
    if not utg_json.exists():
        main_logger.warning('{} not exist, checking nothing'.format(utg_json))
        return False
    try:
        seq = loads(utg_json.read_text())['utg_event_ids_of_test']
    except Exception as e:
        main_logger.error('error when reading sequence from {}'.format(utg_json))
        main_logger.exception(e)
        return False
    if trie_tree.check_seq_valid(seq):
        main_logger.debug('valid seq {}'.format(seq))
        return True
    else:
        if log:
            main_logger.info('{} pruned with prefix {}'.format(mutant, seq))
        if invalid_callback:
            invalid_callback(mutant, seq)
        return False


def run_mutant(
        device: str, apk: str,
        grant_permission: str,
        event_interval: int,
        model: Path, mutant: Path,
        timeout_flag_ref: Value,
        timeout: int,
        ignore_scripts: Optional[List[str]] = None,
        coverage=False,
        memory: Optional[int] = None):
    mutant_log_id = time_str()
    # run mutant
    _cmd = [
        'python3', '-m', 'droidbot.start',
        '-d', device, '-a', apk,
        '-policy', 'fuzzing_run',
        '-o', '{}'.format(model), '-mutant', '{}'.format(mutant),
        '-is_emulator', '{}'.format(grant_permission),
        '-keep_app', '-interval', '{}'.format(event_interval),
    ]
    if memory is not None and memory > 0:
        _cmd += ['-memory-limit', '{}'.format(memory)]
    if ignore_scripts is not None:
        for _s in ignore_scripts:
            _cmd += ['-config-script', _s]
    if coverage:
        _cmd += ['-coverage']
    # fixme: something on MacOS makes this not working, this cause skip not functioning
    # Why this works on Linux?
    # passing logger from main process does not work at all
    # ref: https://docs.python.org/3/howto/logging-cookbook.html#logging-to-a-single-file-from-multiple-processes
    get_logger(device).debug('running {}'.format(' '.join(_cmd)))
    stdout, stderr = None, None
    try:
        get_logger(device).info('run {}'.format(mutant))
        _p = timeout_run(_cmd, timeout=timeout, stdout=PIPE, stderr=PIPE)
        stdout, stderr = _p.stdout, _p.stderr
        timeout_flag_ref.value = False
    except TimeoutExpired as e:
        get_logger(device).warning('`{}` timeout after {}, stdout and stderr are in log file'.format(_cmd, e.timeout))
        stdout, stderr = e.stdout, e.stderr
        timeout_flag_ref.value = True
    finally:
        # get_logger(device).debug('stdout: {}'.format(stdout))
        # get_logger(device).debug('stderr: {}'.format(stderr))
        for t in ('stdout', 'stderr'):
            f = mutant / '{}-{}.log'.format(mutant_log_id, t)
            f.touch()
            f.write_bytes(stdout if t == 'stdout' else stderr)


class TestProcessContext:
    emulator_start_time: float
    mutant_count: int

    starting_thread: Optional[Thread] = None
    running: bool

    emulator: Optional[Popen]

    def start(self):
        if self.async_start:
            self.starting_thread = Thread(target=self._start_emulator)
            self.starting_thread.start()
            # block main thread for 10 seconds
            sleep(10)
        else:
            self._start_emulator()

    def _start_emulator(self):
        while self.running:
            try:
                devices = list_devices()
                debug_assert(self.device_name not in devices)
                self.emulator = emulator_process(self.avd_name, self.emulator_headless, ith=self.device_i)
                self.wait_ready()
                break
            except AssertionError as e:
                self.logger.exception(e)
                self.logger.error('{} already running, will retry after 1 min'.format(self.device_name))
                sleep(60)
            except Exception as e:
                self.logger.exception(e)
                self.kill_emulator()

        self.starting_thread = None
        self.emulator_start_time = time()
        self.mutant_count = 0

    def wait_ready(self):
        return wait_ready(self.device_name)

    def kill_emulator(self):
        if self.emulator is not None:
            self.emulator.kill()
            self.emulator.poll()
            self.emulator = None

    def __init__(self, avd_name, device_i: int, timeout: int,
                 instance_memory_limit: int,
                 model: Test,
                 coverage: bool = False,
                 headless_emulator: bool = True,
                 trie_delete: bool = False,
                 async_start: bool = False) -> None:
        self.avd_name = avd_name
        self.device_i = device_i
        self.model = model
        self.emulator_headless = headless_emulator
        self.memory_limit = instance_memory_limit
        self.trie_delete = trie_delete
        self.coverage = coverage

        self.device_name = ith_emulator_name(self.device_i)
        self.logger = get_logger(self.device_name)

        self.last: Optional[Test] = None
        self.history: RunHistory = []
        self.process: Optional[Process] = None
        self.timeout = timeout
        self.timeout_flag = Value('b', False)
        self.emulator = None

        self.async_start = async_start
        self.running = True
        self.start()
        register(self.stop)

    @property
    def is_available_device(self):
        if self.starting_thread is not None:
            # mutant history is not ready yet
            return False
        if (
                (0 < RESTART_AFTER_MUTANTS < self.mutant_count) or
                (0 < RESTART_AFTER_SECONDS < time() - self.emulator_start_time)
        ):
            self.restart_emulator()
            return False
        return self.process is None or not self.process.is_alive()

    @property
    def process_is_not_none(self):
        return self.process is not None

    @staticmethod
    def pruned_callback(test: Test, seq):
        main_logger.info('{} pruned with prefix {}, deleted'.format(test, seq))
        test.rmdir()

    def run_next(self, test: Test):
        # check emulator by taking a screen shot
        while take_sc(self.device_name, 10) is None:
            self.restart_emulator()
        if self.last is not None:
            main_logger.debug('updating finished test {}'.format(self.last))
            trie_update(self.last)
            self.mutant_count += 1
        if not trie_check_valid(test, not self.trie_delete,
                                invalid_callback=self.pruned_callback if self.trie_delete else None):
            return
        self.last = test
        self.history.append(self.last)
        self.process = Process(target=run_mutant, kwargs={
            'device': self.device_name, 'apk': args.apk, 'model': self.model, 'mutant': test,
            'timeout_flag_ref': self.timeout_flag,
            'timeout': self.timeout,
            'ignore_scripts': args.script,
            'grant_permission': '-grant_perm' if args.grant_permission else "",
            'event_interval': args.interval,
            'coverage': self.coverage,
            'memory': self.memory_limit,
        })
        self.process.start()

    def join(self):
        if self.process is not None:
            self.process.join()

    def count_test(self, t: Test):
        return len([i for i in self.history if i.samefile(t)])

    @property
    def need_retry(self):
        """
        if need to retry last run mutant
        :return: bool
        """
        return (
            # last test timeout
                self.timeout_flag.value
                # no same test run before
                and len([t.samefile(self.last) for t in self.history]) == 0
        )

    def retry_last(self):
        # restart emulator
        get_logger(self.device_name).info('previous {} timeout, restart emulator and rerun test'.format(self.last))

        self.restart_emulator()
        self.wait_ready()
        self.run_next(self.last)

    def restart_emulator(self):
        get_logger(self.device_name).info('restarting')

        self.kill_emulator()
        self.start()

    def stop(self):
        self.running = False
        if self.starting_thread is not None:
            self.starting_thread.join()
        self.kill_emulator()


@lru_cache(1)
# this method will be called with same parameter several times
def test_hash(mutant: Optional[Union[Test, str]] = None,
              seed_id: Optional[int] = None, mutant_id: Optional[int] = None) -> TestHash:
    assert (seed_id is None) == (mutant_id is None)
    assert (seed_id is None) != (mutant is None)
    if mutant is not None:
        if isinstance(mutant, str):
            mutant = Path(mutant)
        seed_id, mutant_id = (
            match(r'seed-test-(\d+)', mutant.parent.name).group(1),
            match(r'mutant-([-\d]+)', mutant.name).group(1)
        )
    return '{}-{}'.format(seed_id, mutant_id)


def need_run_wrap(m: Test, to_skip: Dict[TestHash, str]) -> bool:
    if test_hash(m) not in to_skip:
        return True
    main_logger.info('skip {} from {}'.format(m, to_skip[test_hash(m)]))
    return False


def main(args: Namespace):
    base = Path(args.o)
    mutants = base.glob('seed-tests/seed-test-*/mutant-*')

    if args.test is not None:
        m = Path(args.test)
        assert m.exists()
        mutants = [m]
        args.skip = False

    if args.seeds != 'all':
        ids = set()
        for i in args.seeds.strip(';').split(';'):
            try:
                ids.add('seed-test-{}'.format(int(i)))
            except ValueError:
                ap.error('--seed-to-run error: {}'.format(args.seeds))
        mutants = [i for i in mutants if i.parent.name in ids]
        main_logger.info('running {}'.format(ids))

    global trie_tree
    trie_tree = SeqTrie() if args.trie_reduce else None

    if args.skip or args.trie_load:
        to_skip = {}
        for log_file in base.glob('droidbot-*.log'):
            last_run = {}
            lc = 0
            for line in log_file.read_text().strip().split('\n'):
                lc += 1
                if line.count(' - ') != 3:
                    continue
                _time, _level, log_source, msg = line.split(' - ')
                if _level == 'INFO' and (
                        (log_source.startswith('emulator-') and msg.startswith('run '))
                        or (log_source == 'main' and 'pruned with prefix' in msg)
                ):
                    _m = search(r'seed-tests/seed-test-(\d+)/mutant-([\d-]+)'
                                r'(?: pruned with prefix (?P<pruned_prefix>\[\d+(?:, \d+)*\]))?$', msg)
                    if _m is None:
                        continue
                    test_and_location: Tuple[TestHash, str] = (
                        test_hash(_m.group()),
                        '{}: {}'.format(log_file, lc)
                    )
                    if args.skip:
                        if log_source in last_run:
                            to_skip[last_run[log_source][0]] = last_run[log_source][1]
                        last_run[log_source] = test_and_location
                    if args.trie_load:
                        prefix = _m.group('pruned_prefix')
                        if prefix is None:
                            continue
                        prefix = [int(i) for i in prefix.strip('[]').split(', ')]
                        if trie_tree.check_seq_valid(prefix):
                            main_logger.info('updating trie prefix {} from {}'.format(prefix, test_and_location[1]))
                            trie_tree.update(prefix)
        if to_skip:
            mutants = [i for i in mutants if need_run_wrap(i, to_skip)]

    test_pool: List[TestProcessContext] = []
    for i in range(args.offset, args.offset + args.n):
        test_pool.append(TestProcessContext(args.avd_name, i, args.timeout, args.instance_memory, model=base,
                                            headless_emulator=not args.no_headless,
                                            coverage=args.coverage,
                                            trie_delete=args.trie_delete,
                                            async_start=args.async_start))

    mutants = list(mutants)
    mutant_count = len(mutants)
    for i in range(mutant_count):
        m = mutants[i]
        while True:
            for ctx in test_pool:
                if ctx.is_available_device:
                    if ctx.need_retry:
                        ctx.retry_last()
                        continue
                    else:
                        get_logger('progress').info('running {}/{} on {}'.format(i + 1, mutant_count, ctx.device_name))
                        ctx.run_next(m)
                        break
            else:
                sleep(1)
                continue
            break

    for i in test_pool:
        i.join()

    main_logger.info('Tests finished. Killing emulators.')

    for i in test_pool:
        i.stop()


if __name__ == '__main__':
    ap = ArgumentParser()

    ap.add_argument('-n', type=int, default=16)
    ap.add_argument('--avd', type=str, dest='avd_name', default='base')
    ap.add_argument('--offset', type=int, default=0)
    ap.add_argument('--script', nargs='*', default=[])

    ap.add_argument('-o', required=True)
    ap.add_argument('--apk', required=True)
    ap.add_argument('--no-trie-reduce', dest='trie_reduce', default=True, action='store_false')
    ap.add_argument('--no-trie-load', dest='trie_load', default=True, action='store_false')
    ap.add_argument('--trie-delete', dest='trie_delete', default=False, action='store_true')
    ap.add_argument('--interval', type=int, default=0)
    ap.add_argument('--no-headless', dest='no_headless', action='store_true', default=False)
    ap.add_argument('--timeout', type=int, default=300)
    ap.add_argument('--view_str_backtrack_tree_level', type=int, default=1)
    ap.add_argument('--no-coverage', dest='coverage', action='store_false', default=True,
                    help='Do *NOT* collect coverage data')
    ap.add_argument('--seeds-to-run', '-s', dest='seeds', type=str, default='all',
                    help='\'all\', or ids of seed tests to run, like \'1;2;3\'')

    ap.add_argument('--log', default=None, help='default is <-o>/droidbot-<time>.log')

    # todo: remove this, restart emulator instead
    ap.add_argument('--droidbot-memory-limit', '--memory', dest='instance_memory', default=0, type=int,
                    help='droidbot memory limit in MB')
    ap.add_argument('--no-skip', dest='skip', default=True, action='store_false',
                    help='Do *NOT* skip tests have been run based on all `<-o>/droidbot-<time>.log`')

    ap.add_argument('--test-single-mutant', '--debug', dest='test', default=None,
                    help='Specific one single mutant to run, only for debugging, implies --no-skip.')
    ap.add_argument('--async-start', dest='async_start', action='store_true', default=False)

    ap.add_argument('--no-permission', dest='grant_permission', default=True, action='store_false')

    args = ap.parse_args()

    if args.log is None:
        args.log = Path(args.o) / 'droidbot-{}.log'.format(time_str())

    if args.n + args.offset > 16:
        ap.error('n + offset should not be ge 16')

    if args.trie_reduce:
        if args.trie_delete:
            ap.error('--trie-delete can only work for trie reduce configuration')
    else:
        # not meaningful
        args.trie_load = False

    set_log_file(args.log)

    main(args)
