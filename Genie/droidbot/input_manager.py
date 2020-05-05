import json
import logging
import subprocess
import time

from .input_event import EventLog
from .input_policy import UtgBasedInputPolicy, UtgNaiveSearchPolicy, UtgGreedySearchPolicy, \
    UtgReplayPolicy, \
    ManualPolicy, \
    UtgScriptSearchPolicy, \
    UtgBasedPropertyFuzzingPolicy, \
    WeightedSearchPolicy, \
    POLICY_NAIVE_DFS, POLICY_GREEDY_DFS, \
    POLICY_NAIVE_BFS, POLICY_GREEDY_BFS, \
    POLICY_REPLAY, \
    POLICY_MANUAL, POLICY_MONKEY, POLICY_NONE, POLICY_SCRIPT_EXPLORE, POLICY_PROPERTY_FUZZING, POLICY_WEIGHTED, \
    POLICY_FUZZ_GEN, POLICY_FUZZ_RUN, RunMutantPolicy, POLICY_FUZZ_GEN_SEEDS, POLICY_FUZZ_GEN_MUTANTS

DEFAULT_POLICY = POLICY_GREEDY_DFS
DEFAULT_EVENT_INTERVAL = 1
DEFAULT_EVENT_COUNT = 1000
DEFAULT_TIMEOUT = -1


class UnknownInputException(Exception):
    pass


class InputManager(object):
    """
    This class manages all events to send during app running
    """

    def __init__(self, device, app, policy_name, mutant_gen_n, random_input, event_count, event_interval,
                 script_path=None, profiling_method=None, master=None, replay_output=None,
                 config_script=None, ignore_windows_script_path=None,
                 max_random_seed_test_length=0, max_seed_test_suite_size=0, max_independent_trace_length=0,
                 max_mutants_per_seed_test=0, max_mutants_per_insertion_position=0,
                 seed_of_mutant=None, do_oracle_checking=False, mutant_dir=None, seed_generation_strategy=None,
                 seeds_to_mutate=None, dump_coverage_mode=False):
        """
        manage input event sent to the target device
        :param device: instance of Device
        :param app: instance of App
        :param policy_name: policy of generating events, string
        :return:
        """
        self.logger = logging.getLogger('InputEventManager')
        self.enabled = True

        self.device = device
        self.app = app
        self.policy_name = policy_name
        self.mutant_gen_n = mutant_gen_n
        self.random_input = random_input
        self.events = []
        self.policy = None
        self.script = None
        self.config_script = config_script
        self.ignore_windows_script = None
        self.event_count = event_count
        self.event_interval = event_interval
        self.replay_output = replay_output

        # 
        self.max_random_seed_test_length = max_random_seed_test_length
        self.max_seed_test_suite_size = max_seed_test_suite_size
        self.max_independent_trace_length = max_independent_trace_length
        self.max_mutants_per_seed_test = max_mutants_per_seed_test
        self.max_mutants_per_insertion_position = max_mutants_per_insertion_position
        self.seed_generation_strategy = seed_generation_strategy
        self.seeds_to_mutate = seeds_to_mutate
        self.do_oracle_checking = do_oracle_checking
        self.dump_coverage_mode = dump_coverage_mode

        self.monkey = None

        #  load the droidbot script if exists
        if script_path is not None:
            f = open(script_path, 'r', encoding='utf-8')
            script_dict = json.load(f)
            from .input_script import DroidBotScript
            self.script = DroidBotScript(script_dict)

        #  load the script of ignored windows during model construction
        if ignore_windows_script_path is not None:
            f = open(ignore_windows_script_path, 'r', encoding='utf-8')
            script_dict = json.load(f)
            from .ignore_windows_script import IgnoreWindowsScript
            self.ignore_windows_script = IgnoreWindowsScript(script_dict)

        self.seed_of_mutant = seed_of_mutant
        self.mutant_dir = mutant_dir

        self.policy = self.get_input_policy(device, app, master)
        self.profiling_method = profiling_method

    def get_input_policy(self, device, app, master):
        """
        get the policy for event generation
        """
        if self.policy_name == POLICY_NONE:
            input_policy = None
        elif self.policy_name == POLICY_MONKEY:
            input_policy = None
        elif self.policy_name in [POLICY_NAIVE_DFS, POLICY_NAIVE_BFS]:
            input_policy = UtgNaiveSearchPolicy(device, app, self.random_input, self.policy_name)
        elif self.policy_name in [POLICY_GREEDY_DFS, POLICY_GREEDY_BFS]:
            input_policy = UtgGreedySearchPolicy(device, app, self.random_input, self.policy_name)

        #  new policies
        elif self.policy_name == POLICY_SCRIPT_EXPLORE:
            input_policy = UtgScriptSearchPolicy(device, app, self.random_input, self.policy_name)
        elif self.policy_name in (POLICY_PROPERTY_FUZZING,
                                  POLICY_FUZZ_GEN,
                                  POLICY_FUZZ_GEN_SEEDS,
                                  POLICY_FUZZ_GEN_MUTANTS):
            # the policies related to independent view fuzzing
            input_policy = UtgBasedPropertyFuzzingPolicy(
                device, app, self.random_input, self.config_script,
                mutant_gen_n=self.mutant_gen_n,
                event_interval=self.event_interval,
                max_random_seed_test_length=self.max_random_seed_test_length,
                max_seed_test_suite_size=self.max_seed_test_suite_size,
                max_independent_trace_length=self.max_independent_trace_length,
                max_mutants_per_seed_test=self.max_mutants_per_seed_test,
                max_mutants_per_insertion_position=self.max_mutants_per_insertion_position,
                ignore_windows_script=self.ignore_windows_script,
                seed_generation_strategy=self.seed_generation_strategy,
                seeds_to_mutate=self.seeds_to_mutate,
                dump_coverage_mode=self.dump_coverage_mode)
            input_policy.script = self.script
            if self.policy_name == POLICY_FUZZ_GEN:
                input_policy.mode = 'gen'
            if self.policy_name == POLICY_FUZZ_GEN_SEEDS:
                input_policy.mode = 'gen_seeds'
            if self.policy_name == POLICY_FUZZ_GEN_MUTANTS:
                input_policy.mode = 'gen_mutants'
        elif self.policy_name == POLICY_FUZZ_RUN:
            input_policy = RunMutantPolicy(device, app, self.config_script,
                                           event_interval=self.event_interval,
                                           mutant_dir=self.mutant_dir,
                                           seed_of_mutant=self.seed_of_mutant,
                                           do_oracle_checking=self.do_oracle_checking,
                                           dump_coverage_mode=self.dump_coverage_mode)
        elif self.policy_name == POLICY_WEIGHTED:
            # the weighted exploration policy adapted from Stoat
            input_policy = WeightedSearchPolicy(device, app, self.random_input, self.policy_name,
                                                ignore_windows_script=self.ignore_windows_script)
        # End

        elif self.policy_name == POLICY_REPLAY:
            input_policy = UtgReplayPolicy(device, app, self.replay_output)
        elif self.policy_name == POLICY_MANUAL:
            input_policy = ManualPolicy(device, app)
        else:
            self.logger.warning("No valid input policy specified. Using policy \"none\".")
            input_policy = None
        if isinstance(input_policy, UtgBasedInputPolicy):
            input_policy.script = self.script
            input_policy.master = master
        return input_policy

    def add_event(self, event, output_dir):
        """
        add one event to the event list
        :param event: the event to be added, should be subclass of InputEvent
        :param output_dir: the output dir for storing the original utg
        :return: EventLog, the event log
        """
        if event is None:
            return
        self.events.append(event)

        event_log = EventLog(self.device, self.app, event, self.profiling_method)
        event_log.start()
        while True:
            time.sleep(self.event_interval)
            if not self.device.pause_sending_event:
                break

        event_log.stop(output_dir)

        #  return event_log
        return event_log

    def start(self):
        """
        start sending event
        """
        self.logger.info("start sending events, policy is %s" % self.policy_name)

        try:
            if self.policy is not None:
                self.policy.start(self)
            elif self.policy_name == POLICY_NONE:
                #  just start the app and do nothing
                self.device.start_app(self.app)
                if self.event_count == 0:
                    return
                while self.enabled:
                    time.sleep(1)
            elif self.policy_name == POLICY_MONKEY:
                #  use monkey to send events
                throttle = self.event_interval * 1000
                monkey_cmd = "adb -s %s shell monkey %s --ignore-crashes --ignore-security-exceptions" \
                             " --throttle %d -v %d" % \
                             (self.device.serial,
                              "" if self.app.get_package_name() is None else "-p " + self.app.get_package_name(),
                              throttle,
                              self.event_count)
                self.monkey = subprocess.Popen(monkey_cmd.split(),
                                               stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE)
                for monkey_out_line in iter(self.monkey.stdout.readline, ''):
                    if not isinstance(monkey_out_line, str):
                        monkey_out_line = monkey_out_line.decode()
                    self.logger.info(monkey_out_line)
                # may be disturbed from outside
                if self.monkey is not None:
                    self.monkey.wait()
            elif self.policy_name == POLICY_MANUAL:
                #  do manual exploration
                self.device.start_app(self.app)
                while self.enabled:
                    keyboard_input = input("press ENTER to save current state, type q to exit...")
                    if keyboard_input.startswith('q'):
                        break
                    self.device.get_current_state(self.device.output_dir)

        except KeyboardInterrupt:
            pass

        self.stop()
        self.logger.info("Finish sending events")

    def stop(self):
        """
        stop sending event
        """
        if self.monkey:
            if self.monkey.returncode is None:
                self.monkey.terminate()
            self.monkey = None
            pid = self.device.get_app_pid("com.android.commands.monkey")
            if pid is not None:
                self.device.adb.shell("kill -9 %d" % pid)
        self.enabled = False
