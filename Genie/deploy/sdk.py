from pathlib import Path
from subprocess import run
from tempfile import NamedTemporaryFile

from .utils import assert_package_installed, update_env

sdk_download_url = 'https://dl.google.com/android/repository/sdk-tools-linux-4333796.zip'

bashrc_flag = ('# >>> Android SDK initialize >>>', '# <<< Android SDK initialize <<<')

default_sdk_path = Path.home() / 'sdk'
default_sh_rc = Path.home() / '.bashrc'


def has_sdk(sdk_dir=str(default_sdk_path)):
    return Path(sdk_dir).exists()


def init_sdk(sdk_dir=str(default_sdk_path)):
    assert_package_installed('unzip', 'wget')

    _archive_file = NamedTemporaryFile(delete=False)
    _archive_file.close()

    run(['wget', '-O', _archive_file.name, sdk_download_url])
    run(['unzip', _archive_file.name, '-d', sdk_dir])
    run(['rm', _archive_file.name])

    setup_env()
    setup_sdk_components()


def setup_env(rc=default_sh_rc, sdk_dir=default_sdk_path):
    rc_cont = rc.read_text() if rc.exists() else ''

    if not all(flag in rc_cont for flag in bashrc_flag):
        update_env('ANDROID_SDK_ROOT', sdk_dir)
        update_env('ANDROID_AVD_HOME', Path.home() / '.android' / 'avd')
        update_env('PATH', sdk_dir / 'emulator', append=':')
        update_env('PATH', sdk_dir / 'tools' / 'bin', append=':')

        rc_cont += '\n'.join([
            '',
            bashrc_flag[0],
            'export ANDROID_SDK_ROOT={}'.format(sdk_dir),
            'export ANDROID_AVD_HOME={}'.format(Path.home() / '.android' / 'avd'),
            'export PATH={}:{}:{}:$PATH'.format(sdk_dir / 'emulator',
                                                sdk_dir / 'tools' / 'bin',
                                                sdk_dir / 'platform-tools'),
            bashrc_flag[1],
        ])

    with open(rc, 'w') as f:
        f.write(rc_cont)


def setup_sdk_components():
    assert_package_installed('openjdk-8-jre')
    run("yes | sdkmanager 'system-images;android-23;google_apis;x86'", shell=True)
    run(['sdkmanager', 'emulator', 'platform-tools', 'platforms;android-23'])


if __name__ == '__main__':
    if not has_sdk():
        init_sdk()
