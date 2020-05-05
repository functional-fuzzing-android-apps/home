from subprocess import run

from .emulator import init_avd
from .sdk import init_sdk

if __name__ == '__main__':
    run(['apt-get', 'install', '-y', '-qq', 'wget', 'lib32stdc++6', 'openjdk-8-jre', 'unzip', 'qemu-kvm', 'git', ])
    # run('usermod -a -G kvm $USER', shell=True)
    init_sdk()
    init_avd()
