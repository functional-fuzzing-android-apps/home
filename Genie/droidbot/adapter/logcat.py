import subprocess
import logging
from .adapter import Adapter


class Logcat(Adapter):
    """
    A connection with the target device through logcat.
    """

    def __init__(self, device=None):
        """
        initialize logcat connection
        :param device: a Device instance
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        if device is None:
            from droidbot.device import Device
            device = Device()
        self.device = device
        self.connected = False
        self.process = None
        if device.output_dir is None:
            self.out_file = None
        else:
            self.out_file = "%s/logcat.txt" % device.output_dir

        # 
        self.app_package_name = None
        self.has_crash = False
        self.crash_confidence = None
        self.crash_filter = "AndroidRuntime:E CrashAnrDetector:D ActivityManager:E SQLiteDatabase:E WindowManager:E ActivityThread:E Parcel:E *:F *:S"

    def connect(self):
        self.device.adb.run_cmd("logcat -c")
        self.process = subprocess.Popen(["adb", "-s", self.device.serial, "logcat", "-v", "threadtime",
                                         self.crash_filter],
                                        stdin=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        stdout=subprocess.PIPE)
        import threading
        listen_thread = threading.Thread(target=self.handle_output)
        listen_thread.start()

    def disconnect(self):
        self.connected = False
        if self.process is not None:
            self.process.terminate()

    # 
    def reconnect(self, app_package_name, out_file):
        """
        Reconnect the logcat by filter msg for app_package_name into out_file
        :param app_package_name: the app under check
        :param out_file: the output file of logcat
        :return:
        """
        if out_file is None or app_package_name is None:
            return

        self.disconnect()
        self.out_file = out_file
        self.app_package_name = app_package_name
        self.has_crash = False
        self.crash_confidence = None

        self.device.adb.run_cmd("logcat -c")
        self.process = subprocess.Popen(["adb", "-s", self.device.serial, "logcat", "-v", "threadtime",
                                         self.crash_filter],
                                        stdin=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        stdout=subprocess.PIPE)
        import threading
        listen_thread = threading.Thread(target=self.handle_output)
        listen_thread.start()

    def check_connectivity(self):
        return self.connected

    def handle_output(self):
        self.connected = True

        f = None
        if self.out_file is not None:
            f = open(self.out_file, 'w')

        while self.connected:
            if self.process is None:
                continue
            line = self.process.stdout.readline()
            if not isinstance(line, str):
                line = line.decode()
            self.parse_line(line)
            if f is not None:
                f.write(line)
        if f is not None:
            f.close()
        print("[CONNECTION] %s is disconnected" % self.__class__.__name__)

    # use this function to detect app-wise crashes
    def parse_line(self, logcat_line):

        if self.app_package_name is None:
            # do nothing if which app under test is not specified
            return

        line = logcat_line.split(':', 3)[-1].strip()
        if self.app_package_name in line:
            # this may be crash but not very sure
            self.has_crash = True
            self.crash_confidence = "Medium"
            if "at" in line:
                # this must be an app-wise crash if the crash stack contains the app package name
                # but this condition does not always hold for all crashes
                self.crash_confidence = "High"

    def check_crash(self):
        return self.has_crash

    def get_crash_confidence(self):
        return self.crash_confidence

