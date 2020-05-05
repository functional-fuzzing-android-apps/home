import os
import signal
import subprocess
from time import strftime
from typing import List, Callable, Optional


def dpkg_check_package_installed(name):
    return name in subprocess.run(['dpkg', '-l'], stdout=subprocess.PIPE).stdout.decode()


def apt_check_package_installed(name):
    return '[installed]' in subprocess.run(['apt', '-qq', 'list', name])


def assert_package_installed(*names: str, checker: Callable[[str], bool] = dpkg_check_package_installed):
    not_installed = [name for name in names if not checker(name)]
    assert not not_installed, '{} not installed.'.format(', '.join(not_installed))


def update_env(name, value, append: Optional[str] = None):
    if not isinstance(value, str):
        value = str(value)
    if append is not None:
        _old = os.getenv(name)
        if _old is not None:
            value = _old + append + value
    os.environ[name] = value


def timeout_run(*popenargs, timeout: int, **kwargs) -> subprocess.CompletedProcess:
    """
    fix https://bugs.python.org/issue30154
    """
    with subprocess.Popen(*popenargs, start_new_session=True, **kwargs) as process:
        try:
            pg = os.getpgid(process.pid)
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            for s in (signal.SIGINT, signal.SIGTERM, signal.SIGKILL):
                os.killpg(pg, s)
                try:
                    stdout, stderr = process.communicate(timeout=1)
                    break
                except subprocess.TimeoutExpired:
                    from .logger import get_logger
                    get_logger().error('killing {} failed with {}'.format(process.args, s))
            else:
                stdout, stderr = process.communicate()
            raise subprocess.TimeoutExpired(process.args, timeout, output=stdout, stderr=stderr)
        except:  # Including KeyboardInterrupt, communicate handled that.
            process.kill()
            # We don't call process.wait() as .__exit__ does that for us.
            raise
        retcode = process.poll()
    return subprocess.CompletedProcess(process.args, retcode, stdout, stderr)


class CallTimeoutExpired(subprocess.TimeoutExpired):
    def __init__(self, callee, args, kwargs, timeout: float,
                 output=None, stderr=None) -> None:
        super().__init__(callee, timeout, output, stderr)
        self.call_args = args
        self.call_kwargs = kwargs

    def __str__(self) -> str:
        return "Calling {} with {}, {} timed out after {} seconds".format(
            self.cmd, self.call_args, self.call_kwargs, self.timeout)


def timeout_call(target, _timeout: int, *args, **kwargs):
    def _timeout_handler(_signum, _frame):
        raise CallTimeoutExpired(target, args=args, kwargs=kwargs, timeout=_timeout)

    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(_timeout)
    try:
        res = target(*args, **kwargs)
        signal.alarm(0)
        return res
    except CallTimeoutExpired:
        raise


def adb(cmd: List[str], serial: Optional[str],
        timeout: Optional[int] = 60,
        stdout: int = subprocess.DEVNULL) -> Optional[bytes]:
    _cmd = ['adb']
    if serial is not None:
        _cmd += ['-s', serial]
    _cmd += cmd

    return (subprocess.run(_cmd, stderr=subprocess.DEVNULL, stdout=stdout) if timeout is None else
            timeout_run(_cmd, timeout=timeout, stderr=subprocess.DEVNULL, stdout=stdout)).stdout


def list_devices() -> List[str]:
    _out: str = adb(['devices'], serial=None, stdout=subprocess.PIPE).decode()
    return [i.split('\t', maxsplit=1)[0]
            for i in _out.split('\n')
            if i and i.endswith('\tdevice')]


def debug_assert(cond: bool, msg: Optional[str] = None):
    # used for more convenient breakpoint
    assert cond, msg


def time_str():
    return strftime("%Y-%m%d-%H%M%-S")


class EmulatorError(Exception):
    pass


class WaitTimeout(EmulatorError):
    def __init__(self, cmd: str, device: str, timeout: int, *args: object) -> None:
        super().__init__(*args)

        self.device = device
        self.timeout = timeout
        self.cmd = cmd

    def __str__(self) -> str:
        return 'Waiting for `{}` on {} more than {} seconds'.format(self.cmd, self.device, self.timeout)
