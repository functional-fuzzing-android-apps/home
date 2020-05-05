"""
Helper for emulator management
"""
from argparse import ArgumentParser
from pathlib import Path
from subprocess import DEVNULL, PIPE, Popen, run, TimeoutExpired
from time import sleep, time
from typing import Optional, List

from .logger import get_logger
from .utils import assert_package_installed, WaitTimeout, timeout_run, list_devices, adb


def create_avd(avd_name: str):
    _cmd = "avdmanager create avd --force --name {}" \
           " --package 'system-images;android-23;google_apis;x86'" \
           " --abi google_apis/x86 --sdcard 512M" \
           " --device 'Nexus 7'".format(avd_name)
    _r = run(_cmd, shell=True, stdout=PIPE)
    _log = get_logger('avd')
    (_log.debug if _r.returncode == 0 else _log.warning)(_r.stdout.decode(errors='ignore'))


def init_avd():
    assert_package_installed('lib32stdc++6', 'qemu-kvm')
    create_avd(avd_name='base')


def boot_anim_stopped(serial: str, timeout: int):
    return adb(['shell', 'getprop', 'init.svc.bootanim'],
               serial=serial, timeout=timeout, stdout=PIPE).decode().strip() == 'stopped'


def boot_completed(serial: str, timeout: int):
    return adb(['shell', 'getprop', 'sys.boot_completed'],
               serial=serial, timeout=timeout, stdout=PIPE).decode().strip() == '1'


def wait_ready(device: str, timeout=5 * 60):
    get_logger(device).info('waiting for device')
    start_wait = time()
    current_cmd: str = ''
    try:
        current_cmd = 'wait-for-device'
        timeout_run(['adb', '-s', device, 'wait-for-device'], timeout=timeout)
        while True:
            current_cmd = 'shell getprop init.svc.bootanim'
            if boot_anim_stopped(device, timeout):
                current_cmd = 'shell getprop sys.boot_completed'
                if boot_completed(device, timeout):
                    get_logger(device).info('device ready')
                    return
            if time() - start_wait > timeout:
                break
            sleep(1)
    except TimeoutExpired:
        raise WaitTimeout(current_cmd, device, timeout)


def emulator_process(avd: str,
                     headless=True,
                     ith: Optional[int] = None,
                     read_only=True):
    _cmd = ['emulator', '-no-boot-anim',
            '-gpu', 'swiftshader_indirect',
            '-avd', avd]
    if headless:
        _cmd.append('-no-window')
    if read_only:
        _cmd.append('-read-only')
    if ith is not None:
        ports = (5554 + ith * 2, 5554 + ith * 2 + 1)
        _cmd += ['-ports', '{},{}'.format(*ports)]
    return Popen(_cmd, stderr=PIPE, stdout=PIPE)


def ith_emulator_name(i: int):
    return 'emulator-{}'.format(5554 + i * 2)


def init_emulator(s=None, create: Optional[str] = None, **kwargs):
    p = None
    if create is not None:
        create_avd(create)
        p = emulator_process(create, read_only=False)
        wait_ready(s)

    repo_base = Path(__file__).parent.parent
    for i in ('Android_robot.png', 'password.txt',
              'DroidBot_documentation.docx', 'DroidBot_documentation.pdf',
              'genie_test_report.png',):
        run(['adb', 'push',
             str((repo_base / 'droidbot' / 'resources' / 'dummy_documents' / i).resolve()),
             '/sdcard/'])
    for i in ('Heartbeat.mp3', 'intermission.mp3',):
        run(['adb', 'push',
             str((repo_base / 'droidbot' / 'resources' / 'dummy_documents' / i).resolve()),
             '/storage/emulated/0/Music/'])

    _cmd = ['adb']
    if s is not None:
        _cmd += ['-s', s]
    _cmd += ['shell', 'pm', 'uninstall', '-k', '--user', '0', 'com.android.gallery']
    run(_cmd)

    if create:
        assert p is not None
        adb(['shell', 'reboot', '-p'], serial=s)
        p.poll()


def run_avd(avd, headless, **kwargs):
    p = emulator_process(avd, headless=headless)
    p.poll()
    print(p.stdout.read())
    print(p.stderr.read())


if __name__ == '__main__':
    ap = ArgumentParser()

    sub_p = ap.add_subparsers(title='action', dest='action')

    init_p = sub_p.add_parser('init')
    init_p.add_argument('--create', default=None, help='avd name to create')
    init_p.add_argument('-s', default=None, help='serial')
    init_p.set_defaults(run=init_emulator)

    test_p = sub_p.add_parser('test')
    test_p.add_argument('avd')
    test_p.add_argument('--headless', default=False, action='store_true')
    test_p.set_defaults(run=run_avd)

    args = vars(ap.parse_args())
    args.pop('run')(**args)
