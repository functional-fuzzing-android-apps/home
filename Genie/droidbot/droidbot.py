# This file contains the main class of droidbot
# It can be used after AVD was started, app was installed, and adb had been set up properly
# By configuring and creating a droidbot instance,
# droidbot will start interacting with Android in AVD like a human
import json
import logging
import os
import sys
from typing import Union

import pkg_resources
import shutil
from threading import Timer

from .device import Device
from .app import App
from .env_manager import AppEnvManager
from .input_manager import InputManager


class DroidBot(object):
    """
    The main class of droidbot
    """
    # this is a single instance class
    instance = None

    def __init__(self, app_path=None, device_serial=None, is_emulator=False, output_dir=None, env_policy=None,
                 policy_name=None, random_input=False, script_path=None, event_count=None, event_interval=None,
                 timeout=None, keep_app=None, keep_env=False, cv_mode=False, uiautomator_mode=False, debug_mode=False,
                 profiling_method=None, grant_perm=False, enable_accessibility_hard=False, master=None, humanoid=None,
                 ignore_ad=False, replay_output=None, config_script_path=None, ignore_windows_script_path=None,
                 max_random_seed_test_length=0, max_seed_test_suite_size=0, max_independent_trace_length=0,
                 max_mutants_per_seed_test=0, max_mutants_per_insertion_position=0,
                 seed_of_mutant=None, mutant_dir=None, seed_generation_strategy=None, seeds_to_mutate="all",
                 do_oracle_checking=False,
                 utg_abstraction_strategy=None, view_context_str_backtrack_level=None, dump_coverage_mode=False,
                 mutant_gen_n: Union[bool, int] = False):
        """
        initiate droidbot with configurations
        :return:
        """
        logging.basicConfig(level=logging.DEBUG if debug_mode else logging.INFO)

        self.logger = logging.getLogger('DroidBot')
        DroidBot.instance = self

        #  check whether we are in the parallel mode (i.e., we will execute a set of mutant tests in parallel)
        if mutant_dir is not None:
            enable_parallel_mode = True
        else:
            enable_parallel_mode = False

        self.output_dir = output_dir
        if (output_dir is not None) and (not enable_parallel_mode):
            if not os.path.isdir(output_dir):
                os.makedirs(output_dir)
            html_index_path = pkg_resources.resource_filename("droidbot", "resources/index.html")
            shutil.copy(html_index_path, output_dir)

        #  load the script of ignored views
        self.config_script = None
        if config_script_path is not None:
            f = open(config_script_path, 'r', encoding='utf-8')
            script_dict = json.load(f)
            from .config_script import ConfigurationScript
            self.config_script = ConfigurationScript(script_dict)

        self.timeout = timeout
        self.timer = None
        self.keep_env = keep_env
        self.keep_app = keep_app

        self.device = None
        self.app = None
        self.droidbox = None
        self.env_manager = None
        self.input_manager = None
        self.enable_accessibility_hard = enable_accessibility_hard
        self.humanoid = humanoid
        self.ignore_ad = ignore_ad
        self.replay_output = replay_output

        self.enabled = True

        try:

            self.app = App(app_path, output_dir=self.output_dir)

            self.device = Device(
                device_serial=device_serial,
                is_emulator=is_emulator,
                output_dir=self.output_dir,
                cv_mode=cv_mode,
                app_package_name=self.app.package_name,
                #  add the parameter
                uiautomator_mode=uiautomator_mode,
                grant_perm=grant_perm,
                enable_accessibility_hard=self.enable_accessibility_hard,
                humanoid=self.humanoid,
                ignore_ad=ignore_ad,
                ignore_views=self.config_script,
                enable_parallel_mode=enable_parallel_mode,
                utg_abstraction_strategy=utg_abstraction_strategy,
                policy_name=policy_name,
                view_context_str_backtrack_level=view_context_str_backtrack_level)

            self.env_manager = AppEnvManager(
                device=self.device,
                app=self.app,
                env_policy=env_policy)

            self.input_manager = InputManager(
                device=self.device,
                app=self.app,
                policy_name=policy_name,
                mutant_gen_n=mutant_gen_n,
                random_input=random_input,
                event_count=event_count,
                event_interval=event_interval,
                script_path=script_path,
                profiling_method=profiling_method,
                master=master,
                replay_output=replay_output,
                config_script=self.config_script,
                ignore_windows_script_path=ignore_windows_script_path,
                max_random_seed_test_length=max_random_seed_test_length,
                max_seed_test_suite_size=max_seed_test_suite_size,
                max_independent_trace_length=max_independent_trace_length,
                max_mutants_per_seed_test=max_mutants_per_seed_test,
                max_mutants_per_insertion_position=max_mutants_per_insertion_position,
                seed_of_mutant=seed_of_mutant,
                mutant_dir=mutant_dir,
                seed_generation_strategy=seed_generation_strategy,
                seeds_to_mutate=seeds_to_mutate,
                do_oracle_checking=do_oracle_checking,
                dump_coverage_mode=dump_coverage_mode)

        except Exception:
            import traceback
            traceback.print_exc()
            self.stop()
            sys.exit(-1)

    @staticmethod
    def get_instance():
        if DroidBot.instance is None:
            print("Error: DroidBot is not initiated!")
            sys.exit(-1)
        return DroidBot.instance

    def start(self):
        """
        start interacting
        :return:
        """

        if not self.enabled:
            return

        if "dummy" in self.device.serial:
            self.input_manager.start()
            self.device = None
            return

        self.logger.info("Starting DroidBot")

        try:
            if self.timeout > 0:
                self.timer = Timer(self.timeout, self.stop)
                self.timer.start()

            self.device.set_up()

            if not self.enabled:
                return
            self.device.connect()

            if not self.enabled:
                return

            self.device.install_app(self.app)

            if not self.enabled:
                return
            self.env_manager.deploy()

            if not self.enabled:
                return
            if self.droidbox is not None:
                self.droidbox.set_apk(self.app.app_path)
                self.droidbox.start_unblocked()
                self.input_manager.start()
                self.droidbox.stop()
                self.droidbox.get_output()
            else:
                #  the entry point to start ripping
                self.input_manager.start()

        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt.")
            pass
        except Exception:
            import traceback
            traceback.print_exc()
            self.stop()
            sys.exit(-1)

        self.stop()
        self.logger.info("DroidBot Stopped")

    def stop(self):
        self.enabled = False
        if self.timer and self.timer.isAlive():
            self.timer.cancel()
        if self.env_manager:
            self.env_manager.stop()
        if self.input_manager:
            self.input_manager.stop()
        if self.droidbox:
            self.droidbox.stop()
        if self.device:
            self.device.disconnect()
        if not self.keep_env:
            self.device.tear_down()
        if not self.keep_app:
            self.device.uninstall_app(self.app)
        if hasattr(self.input_manager.policy, "master") and \
                self.input_manager.policy.master:
            import xmlrpc.client
            proxy = xmlrpc.client.ServerProxy(self.input_manager.policy.master)
            proxy.stop_worker(self.device.serial)


class DroidBotException(Exception):
    pass
