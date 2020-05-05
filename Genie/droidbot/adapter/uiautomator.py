# TODO
# create the adapter uiautomator, which inherits from Adapter
# implement the five basic methods (connect/disconnect/setup/teardown/checkconnectivity) in the parent class
# implement "get_views()", this is the most important method, we may/may not need to adapt our previous view
# structure into DroidBot view

import logging
import traceback

from .adapter import Adapter
from uiautomator import Device as uDevice


class UiautomatorWrapperConnException(Exception):
    """
    Exception in uiautomator wrapper connection
    """
    pass


class UiautomatorWrapperConn(Adapter):
    """
    a connection with uiautomator wrapper.
    """

    def __init__(self, device=None):
        """
        initiate a uiautomator wrapper connection
        :param device: instance of Device
        :return:
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        if device is None:
            from droidbot.device import Device
            device = Device()
        self.device = device
        self.connected = False
        self.uiautomator_device = None

    def set_up(self):
        """
        set up the uiautomator wrapper
        :return:
        """
        self.logger.info("uiautomator wrapper was set up.")
        pass

    def tear_down(self):
        pass

    def connect(self):
        self.uiautomator_device = uDevice(self.device.get_device_serial())
        try:
            out = self.uiautomator_device.info
            print(out)
            # the keyword "sdkInt" should always appear in the output of device.info
            # Example: {'currentPackageName': 'com.android.launcher3', 'displayHeight': 1216,
            #   'displayRotation': 0, 'displaySizeDpX': 601, 'displaySizeDpY': 962, 'displayWidth': 800,
            #   'productName': 'sdk_google_phone_x86', 'screenOn': True, 'sdkInt': 23, 'naturalOrientation': True}
            if "sdkInt" in out:
                self.connected = True
        except IOError:
            traceback.print_exc()
            self.connected = False
            raise UiautomatorWrapperConnException

    def disconnect(self):
        pass

    def check_connectivity(self):
        return self.connected

    def get_views(self):
        """
        get the views of the current UI page
        :return:
        """


if __name__ == "__main__":
    print("Test uiautomator wrapper")
    uiautomator_wrapper_conn = UiautomatorWrapperConn()
    uiautomator_wrapper_conn.set_up()
