import re
import subprocess
import sys
import json
import logging
import random
import os
import copy
import threading
import time
import datetime
from multiprocessing.pool import ThreadPool
from typing import Dict, Optional, List, Tuple
from abc import abstractmethod

import Levenshtein
import pygtrie

from time import strftime

from droidbot.random_weighted_policy import WeightedRandomExplorationPolicy
from .input_event import InputEvent, KeyEvent, IntentEvent, TouchEvent, ManualEvent, SetTextEvent, ScrollEvent, \
    LongTouchEvent, RestartEvent, NOPEvent, EventLog
from .utg import UTG
from .device_state import DeviceState, COLOR_BLUE, CurrentStateNoneException
from .gui_test import GUITestCase, EXECUTION_RESULT_NOT_FULLY_REPLAYABLE, TEST_TAG_SEED_TEST, TEST_TAG_MUTANT_TEST, \
    TEST_TAG_DYNAMIC_TEST

# Max number of restarts
MAX_NUM_RESTARTS = 5
# Max number of steps outside the app
MAX_NUM_STEPS_OUTSIDE = 5
MAX_NUM_STEPS_OUTSIDE_KILL = 10
# Max number of replay tries
MAX_REPLY_TRIES = 5

# Some input event flags
EVENT_FLAG_STARTED = "+started"
EVENT_FLAG_START_APP = "+start_app"
EVENT_FLAG_STOP_APP = "+stop_app"
EVENT_FLAG_EXPLORE = "+explore"
EVENT_FLAG_NAVIGATE = "+navigate"
EVENT_FLAG_TOUCH = "+touch"
EVENT_FLAG_FRESH_RESTART = "+fresh_restart"

#  some input event types
EVENT_TYPE_SCRIPT = "script"
EVENT_TYPE_EXPLORE = "explore"
# End

# Policy taxanomy
POLICY_NAIVE_DFS = "dfs_naive"
POLICY_GREEDY_DFS = "dfs_greedy"
POLICY_NAIVE_BFS = "bfs_naive"
POLICY_GREEDY_BFS = "bfs_greedy"
POLICY_WEIGHTED = "weighted"
POLICY_REPLAY = "replay"
POLICY_MANUAL = "manual"
POLICY_MONKEY = "monkey"
POLICY_NONE = "none"
#  add the new input policy that explores GUIs based on human scripts
POLICY_SCRIPT_EXPLORE = "script_explore"
POLICY_PROPERTY_FUZZING = "fuzzing"     # generate seed tests and their mutant tests and execute mutant tests
POLICY_FUZZ_GEN = 'fuzzing_gen'     # generate seed tests and their mutant tests but do not execute mutant tests
POLICY_FUZZ_GEN_SEEDS = 'fuzzing_gen_seeds'  # only generate seed tests
POLICY_FUZZ_GEN_MUTANTS = 'fuzzing_gen_mutants'  # only generate mutants from given seed tests
POLICY_FUZZ_RUN = 'fuzzing_run'     # run one mutant test


class InputInterruptedException(Exception):
    pass


class InputPolicy(object):
    """
    This class is responsible for generating events to stimulate more app behaviour
    It should call AppEventManager.send_event method continuously.
    """

    def __init__(self, device, app):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.device = device
        self.app = app
        self.master = None
        self.last_event_log = None

    def start(self, input_manager):
        """
        start producing events
        :param input_manager: instance of InputManager
        """
        count = 0
        self.device.get_current_state(self.device.output_dir)
        while input_manager.enabled and count < input_manager.event_count:
            try:
                # make sure the first event is go to HOME screen
                # the second event is to start the app
                if count == 0 and self.master is None:
                    event = KeyEvent(name="HOME")
                elif count == 1 and self.master is None:
                    event = IntentEvent(self.app.get_start_intent())
                else:
                    event = self.generate_event()
                # print("before event execution--: %s" % str(datetime.datetime.now()))
                self.last_event_log = input_manager.add_event(event, self.device.output_dir)
                self.logger.warning("current time: %s, #fired events: %d" % (str(datetime.datetime.now()), count))
            except KeyboardInterrupt:
                break
            except InputInterruptedException as e:
                self.logger.warning("stop sending events: %s" % e)
                break
            # except RuntimeError as e:
            #     self.logger.warning(e.message)
            #     break
            except CurrentStateNoneException as e:
                self.logger.warning("the current state is None: %s" % e)
                break
            except Exception as e:
                self.logger.warning("exception during sending events: %s" % e)
                import traceback
                traceback.print_exc()
                continue
            count += 1

    @abstractmethod
    def generate_event(self):
        """
        generate an event
        @return:
        """
        pass


class NoneInputPolicy(InputPolicy):
    """
    do not send any event
    """

    def __init__(self, device, app):
        super(NoneInputPolicy, self).__init__(device, app)

    def generate_event(self):
        """
        generate an event
        @return:
        """
        return None


class UtgBasedPropertyFuzzingPolicy(InputPolicy):
    """
    utg-based property fuzzing policy
    """

    # Max length of each random Monkey test
    # [input_manager.event_count, MAX_RANDOM_MONKEY_TEST_LENGTH] determines how many seed GUI tests we can generate
    MAX_RANDOM_MONKEY_TEST_LENGTH = 5

    # Max length of each independent trace
    # [input_manager.event_count, MAX_RANDOM_MONKEY_TEST_LENGTH, MAX_INDEPENDENT_TRACE_LENGTH] determines how many
    #   mutant GUI tests we can generate
    MAX_INDEPENDENT_TRACE_LENGTH = 3

    # Seed test generation strategies
    MONKEY_RANDOM_SEED_GENERATION = "random"
    MODEL_BASED_RANDOM_SEED_GENERATION = "model"

    # mutant run mode
    # default for single-thread run
    # fuzz for test generation
    # run for run mutated test
    _available_modes = {'default', 'gen', 'gen_seeds', 'gen_mutants', 'run'}
    mode = 'default'

    @property
    def mode_check(self):
        return self.mode in self._available_modes

    @property
    def mode_gen(self):
        return self.mode in {'default', 'gen'}

    @property
    def mode_gen_seeds(self):
        return self.mode in {'default', 'gen_seeds'}

    @property
    def mode_gen_mutants(self):
        return self.mode in {'default', 'gen_mutants'}

    @property
    def mode_run(self):
        return self.mode in {'default', 'run'}

    @property
    def mode_only_run(self):
        return self.mode in {'run'}

    def __init__(self, device, app, random_input, config_script, mutant_gen_n,
                 event_interval=0,
                 ignore_windows_script=None,
                 max_random_seed_test_length=0,
                 max_seed_test_suite_size=0,
                 max_independent_trace_length=0,
                 max_mutants_per_seed_test=100000,
                 max_mutants_per_insertion_position=100000,
                 seed_generation_strategy=None,
                 seeds_to_mutate=None,
                 dump_coverage_mode=False):

        super(UtgBasedPropertyFuzzingPolicy, self).__init__(device, app)

        self.mutant_gen_n = mutant_gen_n

        self.random_input = random_input
        self.config_script = config_script

        self.ignore_windows_script = ignore_windows_script
        self.event_interval = event_interval
        self.dump_coverage_mode = dump_coverage_mode

        # Max length of each random Monkey test
        # [input_manager.event_count / self.max_random_seed_test_length] determines how many seed GUI tests we
        #   can generate.
        self.max_random_seed_test_length = int(max_random_seed_test_length)

        # Max length of each independent trace
        # [input_manager.event_count, self.max_random_seed_test_length, self.max_independent_trace_length]
        #   determines how many mutant GUI tests we can generate
        self.max_independent_trace_length = int(max_independent_trace_length)

        self.max_mutants_per_seed_test = int(max_mutants_per_seed_test)
        self.max_mutants_per_insertion_position = int(max_mutants_per_insertion_position)

        # the randomly generated GUI tests for mutation, {"seed-test-1": GUITestCase}
        self.seed_tests: Dict[str, GUITestCase] = {}

        # random model-based seed test generation strategy
        self.model_based_random_seed_tests: List[List[Dict]] = []
        self.model_based_seed_test_event_index = 0  # refer to an event in a seed test
        self.model_based_seed_test_index = 0  # refer to a test in the seed test suite

        self.last_event = None  # the last executed event (type of InputEvent)

        # the last logged event (type of EventLog, a informative wrapper of InputEvent)
        self.last_event_log: Optional[EventLog] = None

        self.last_state = None  # the last state before executing the generated event
        self.current_state = None  # the current state after executing the generated event

        self.utg_dir = device.output_dir  # the dir for reading utg
        assert (
                self.utg_dir is not None and
                os.path.exists(self.utg_dir)
        ), "No utg dir is given, please specify via the \"-o\" or \"-output_dir\" option. \n" + \
           " Or has you already constructed the utg model?"

        self.seed_tests_dir = os.path.join(device.output_dir, "seed-tests")  # the dir for storing seed tests
        if not os.path.exists(self.seed_tests_dir):
            os.makedirs(self.seed_tests_dir)
        self.seed_test_cnt = 0
        self.max_seed_test_suite_size = int(max_seed_test_suite_size)
        if not self.mode_only_run:
            self.seed_test_next_id = self.get_next_seed_test_id(self.seed_tests_dir)

        # the original utg constructed during model construction
        self.original_utg = UTG(device=device, app=app, random_input=random_input)

        # the clustered utg of the original utg, used for test mutation
        self.clustered_utg = UTG(device=device, app=app, random_input=random_input)

        # Strategy of seed test generation
        #   "model": generate seed tests from the constructed model (the clustered utg in particular)
        #   "random": generate random seed tests like Google Android Monkey
        self.seed_test_generation_strategy = seed_generation_strategy

        self.seeds_to_mutate = seeds_to_mutate

        # do we start to record a new seed test?
        self.is_new_seed_test: bool = True
        # the current seed test
        self.current_seed_test: Optional[GUITestCase] = None

        #  the default setting is True
        self.enable_update_utg = True
        self.enable_update_original_utg = True

        # By default, one single thread is used to generate/execute the mutant test
        self.parallel_run_mode = False

        # Trie structure to record and discard unreplable mutant test
        # See: https://pypi.org/project/pygtrie/
        self.unreplayable_test_prefix_set = pygtrie.PrefixSet(factory=pygtrie.StringTrie)

        self.random_monkey_gui_exploration_event_count = 0
        self.__nav_target = None
        self.__nav_num_steps = -1
        self.__num_restarts = 0
        self.__num_steps_outside = 0
        self.__event_trace = ""
        self.__missed_states = set()
        self.__random_explore = False

        self.seed_test_generation_exception = False

        # script
        self.script = None
        self.script_events = []
        self.script_event_idx = 0

        # random seed generation policy
        self.random_seed_generation_policy = WeightedRandomExplorationPolicy(
            self.device,
            self.app,
            self.random_input,
            self.ignore_windows_script)
        self.is_script_activated = False
        self.script_activated_event = None

    @staticmethod
    def get_next_seed_test_id(seed_tests_dir):
        seed_tests = [name for name in os.listdir(seed_tests_dir) if os.path.isdir(os.path.join(seed_tests_dir, name))]
        next_seed_test_id = 0
        for seed_test_name in seed_tests:
            if "seed-test-" in seed_test_name:
                seed_test_id = int(seed_test_name.replace("seed-test-", ""))
                if seed_test_id > next_seed_test_id:
                    next_seed_test_id = seed_test_id
        return next_seed_test_id + 1

    @staticmethod
    def generate_model_based_random_seed_tests(utg: UTG, max_seed_test_length, max_seed_test_suite_size):
        """
        Generate seed tests from the utg model
        Specifically, we select the clustered utg as the test generation model.
        :param utg: the utg model to generate seed tests
        :param max_seed_test_length: the max length of one seed test
        :param max_seed_test_suite_size:  the max size of seed test suite
        :return: List[List[Dict]], list of generated seed tests
        """

        # Data structure:
        #   int: the utg event id
        #   int: the selected times during utg-based seed generation
        event_selection_times_history: Dict[int, int] = {}
        # Data structure:
        #   Dict: the event dict that corresponds to utg's events,
        #       i.e., {"event" : event, "id": utg_event_id}
        seed_test_suite: List[List[Dict]] = []

        # # TODO need to be removed, just for debugging, for ``diary-activity-issue 118``
        # Activity Diary
        # seed_test_suite: List[List[Dict]] = [[{'id': 1},
        #                                       {'id': 7},
        #                                       {'id': 10},
        #                                       {'id': 11},
        #                                       {'id': 50},
        #                                       {'id': 27},
        #                                       {'id': 40},
        #                                       {'id': 41},
        #                                       {'id': 42},
        #                                       {'id': 43},
        #                                       {'id': 45},
        #                                       {'id': 46}]]
        # return seed_test_suite
        # # TODO need to be removed, just for debugging, for ``tasks-issue 811``
        # seed_test_suite: List[List[Dict]] = [[{'id': 22},
        #                                       {'id': 2},
        #                                       {'id': 3},
        #                                       {'id': 4},
        #                                       {'id': 4},
        #                                       {'id': 9}
        #                                       ]]
        # return seed_test_suite
        # TODO need to be removed, just for debugging, for ``tasks-issue 816``
        # seed_test_suite: List[List[Dict]] = [[{'id': 12},
        #                                       {'id': 23},
        #                                       {'id': 4},
        #                                       {'id': 5},
        #                                       {'id': 5},
        #                                       {'id': 16},
        #                                       {'id': 17}
        #                                       ]]
        # return seed_test_suite
        # # TODO END

        # TODO need to be removed, just for debugging, for ``unit-converter-issue 170``
        # seed_test_suite: List[List[Dict]] = [[{'id': 1},
        #                                       {'id': 2},
        #                                       {'id': 3},
        #                                       {'id': 5},
        #                                       {'id': 7}
        #                                       ]]
        # return seed_test_suite

        current_test_suite_size = 0
        first_state_str = utg.first_state_str

        while current_test_suite_size < max_seed_test_suite_size:

            current_seed_test: List[Dict] = []
            current_seed_test_str = ""
            current_seed_test_length = 0

            next_state_str = first_state_str

            while current_seed_test_length < max_seed_test_length:

                # data structure:
                #   Dict: event info (including input event, event id)
                #   str: the end state str
                #   int: the selection times of this event
                candidate_events: List[Tuple[Dict, str, int]] = []
                min_event_selection_times = sys.maxsize  # the minimum selection times for an event

                # get the out edges of the current state
                for (start_state_str, end_state_str, events) in \
                        utg.G.out_edges(nbunch=next_state_str, data="events"):

                    for event_str in events:
                        # collect candidate events
                        utg_event_dict = events[event_str]
                        event_id = utg_event_dict['id']
                        if event_id not in event_selection_times_history:
                            # create the selection history for these events
                            event_selection_times_history[event_id] = 0
                        if min_event_selection_times > event_selection_times_history[event_id]:
                            # get the minimum selection times
                            min_event_selection_times = event_selection_times_history[event_id]
                        candidate_events.append(
                            (utg_event_dict, end_state_str, event_selection_times_history[event_id]))

                if len(candidate_events) == 0:
                    # stop the search if we reach an ending state in the utg
                    break

                # only select the event whose selection times is fewest
                filtered_candidate_events = list(filter(lambda x: x[2] == min_event_selection_times, candidate_events))

                # random selection
                (selected_event_dict, end_state_str, _) = \
                    filtered_candidate_events[random.randint(0, len(filtered_candidate_events) - 1)]
                # print("\t -(%d)-> " % selected_event_dict['id'])
                current_seed_test_str += (" -(%d)-> " % selected_event_dict['id'])

                # deepcopy the event dict to avoid disturbing the utg itself
                current_seed_test.append(copy.deepcopy(selected_event_dict))
                current_seed_test_length += 1

                # increase selection times
                event_selection_times_history[selected_event_dict['id']] += 1

                # update the next state
                next_state_str = end_state_str

            seed_test_suite.append(current_seed_test)
            print("the seed test [%d]: %s" % (current_test_suite_size + 1, current_seed_test_str))
            current_test_suite_size += 1

        edge_coverage = len(event_selection_times_history) * 1.0 / utg.effective_event_count
        print("the edge coverage: %f(=%d/%d)" % (edge_coverage,
                                                 len(event_selection_times_history),
                                                 len(utg.G.edges)))
        return seed_test_suite

    def generate_random_seed_tests(self, input_manager, generation_strategy):
        """
        :param input_manager:
        :param generation_strategy:
        :return:
        """

        # clean the execution env before the seed generation
        # 1. Execute FRESH_RESTART event before executing each mutant test
        fresh_restart_event = RestartEvent(self.app.get_start_intent(), self.app.get_package_name(),
                                           self.device.get_granted_runtime_permissions())
        fresh_restart_event.send(self.device)

        count = 0
        self.device.get_current_state(self.device.output_dir)
        while input_manager.enabled and count < input_manager.event_count:
            try:

                if self.is_new_seed_test:
                    # create a new seed test
                    seed_test_id = "seed-test-" + str(self.seed_test_next_id)
                    seed_test_output_dir = os.path.join(self.seed_tests_dir, seed_test_id)
                    self.current_seed_test = GUITestCase(self.device, self.app, self.random_input,
                                                         test_id=seed_test_id,
                                                         test_output_dir=seed_test_output_dir,
                                                         test_tag=TEST_TAG_SEED_TEST)
                    # restart the logcat before test execution
                    self.device.logcat.reconnect(self.app.package_name, self.current_seed_test.logcat_file)
                    self.is_new_seed_test = False

                # make sure the first event is go to HOME screen, the second event is to start the app.
                # these two beginning events will not be included into utg
                if count == 0 and self.master is None:
                    event = KeyEvent(name="HOME")
                    self.last_event_log = input_manager.add_event(event, self.device.output_dir)
                elif count == 1 and self.master is None:
                    event = IntentEvent(self.app.get_start_intent())
                    self.last_event_log = input_manager.add_event(event, self.device.output_dir)
                else:

                    if generation_strategy == UtgBasedPropertyFuzzingPolicy.MONKEY_RANDOM_SEED_GENERATION:
                        event = self.generation_event_by_monkey()
                    elif generation_strategy == UtgBasedPropertyFuzzingPolicy.MODEL_BASED_RANDOM_SEED_GENERATION:
                        event = self.generate_event_by_model()
                    else:
                        self.logger.error("fail to specify seed test generation strategy!")
                        raise Exception

                    if event is None:
                        # stop the seed test generation if the returned event is None
                        count = input_manager.event_count - 1

                    if count == input_manager.event_count - 1:
                        # We do not execute the event if this is the last event.
                        # If the event is executed and logged, it will not be included into the utg because
                        #   the utg update needs to be finished in the next iteration (ie, self.generate_event())
                        # This fixes the issue of reading offline seed tests:
                        #   it will read the last event log but cannot find the to_state of this event.
                        # But this issue does not matter if we do not reuse offline seed tests.
                        return

                    if type(event) is RestartEvent:
                        # disable the update of test utg
                        self.enable_update_utg = False
                        # We execute but do not log RestartEvent since it is only used to start a fresh new test
                        self.last_event_log = input_manager.add_event(event, self.device.output_dir)
                        self.is_new_seed_test = True

                    else:
                        # enable the update of test utg
                        self.enable_update_utg = True
                        self.last_event_log = EventLog(self.device, self.app, event)
                        # record this event log's event id in the test utg (must be set before execution)
                        self.last_event_log.set_utg_event_id(self.current_seed_test.utg.input_event_count + 1)
                        self.last_event_log.run(self.device.output_dir,
                                                event_interval=self.event_interval)

                        # record randomly generated tests
                        self.current_seed_test.add_event_log(self.last_event_log)

                        if self.current_seed_test.test_id not in self.seed_tests:
                            self.seed_tests[self.current_seed_test.test_id] = self.current_seed_test

            except KeyboardInterrupt:
                self.seed_test_generation_exception = True
                break
            except InputInterruptedException as e:
                self.seed_test_generation_exception = True
                self.logger.warning("stop sending events: %s" % e)
                break
            # except RuntimeError as e:
            #     self.logger.warning(e.message)
            #     break
            except CurrentStateNoneException as e:
                self.seed_test_generation_exception = True
                self.logger.warning("the current state is None: %s" % e)
                break
            except Exception as e:
                self.logger.warning("exception during sending events: %s" % e)
                import traceback
                traceback.print_exc()
                continue
            count += 1

    def generate_event_by_model(self):
        """
        model-based random seed generation
        :return:
        """
        # Get current device state (be careful, when assigning self.current_state, which maintains a lot of information)
        self.current_state = self.device.get_current_state(self.device.output_dir)
        if self.current_state is None:
            #  If cannot get the current state, BACK
            time.sleep(5)
            return KeyEvent(name="BACK")

        #  update utg
        if self.enable_update_utg:
            self.update_utg_during_random_seed_generation()

        event = self.concretize_model_based_random_seed_tests(self.current_state)

        # model-based random seed generation
        if event is not None:
            pass

        else:
            self.seed_test_cnt += 1  # create a new test id
            self.seed_test_next_id += 1

            if self.model_based_seed_test_event_index == 0:

                # dump the coverage data before restart the app
                if self.dump_coverage_mode:
                    try:
                        remote_coverage_data_file_path = "/data/data/" + self.app.get_package_name() + "/files/coverage.ec"
                        local_coverage_data_file_path = self.current_seed_test.test_output_dir
                        self.device.dump_coverage(remote_coverage_data_file_path, local_coverage_data_file_path)
                    except subprocess.CalledProcessError as e:
                        print("the error was caught !!!")
                        print(e.output)

                event = RestartEvent(self.app.get_start_intent(), self.app.get_package_name(),
                                     self.device.get_granted_runtime_permissions())

            if self.model_based_seed_test_index >= self.max_seed_test_suite_size:
                event = None

            # TODO, need to remove, just for debug
            # self.model_based_seed_test_index = 101

        #  update the last state and event
        self.last_state = self.current_state
        self.last_event = event
        return event

    def generation_event_by_monkey(self):
        """
        monkey-based random seed generation
        @return:
        """
        # Get current device state (be careful, when assigning self.current_state, which maintains a lot of information)
        self.current_state = self.device.get_current_state(self.device.output_dir)
        if self.current_state is None:
            #  If cannot get the current state, BACK
            time.sleep(5)
            return KeyEvent(name="BACK")

        #  update utg
        if self.enable_update_utg:
            self.update_utg_during_random_seed_generation()

        event = None

        # if the previous operation is not finished, continue
        if len(self.script_events) > self.script_event_idx:
            #  debug
            print("if the previous operation is not finished, continue ...")
            event = self.script_events[self.script_event_idx].get_transformed_event(self)
            if event is None:
                self.logger.warning('script do not match view, stop sending script events')
                self.script_events = []
                self.script_event_idx = 0
            else:
                self.script_event_idx += 1

                # count number of executed events
                self.random_monkey_gui_exploration_event_count += 1

        # First try matching a state defined in the script
        if event is None and self.script is not None:
            #  debug
            # print("First try matching a state defined in the script ...")
            operation = self.script.get_operation_based_on_state(self.current_state)
            if operation is not None:
                self.script_events = operation.events
                # restart script
                event = self.script_events[0].get_transformed_event(self)
                self.script_event_idx = 1

                # count number of executed events
                self.random_monkey_gui_exploration_event_count += 1

                # set flag variables for the seed generation policy
                self.is_script_activated = True
                self.script_activated_event = self.last_event

        if event is None:
            # Random GUI exploration mode
            if self.random_monkey_gui_exploration_event_count < self.max_random_seed_test_length:

                # count number of executed events
                self.random_monkey_gui_exploration_event_count += 1

                # Previously, we use pure random seed test generation
                # event = self.__monkey_based_random_gui_exploration(self.current_state)

                # Now, we use weighted random seed test generation
                event = self.random_seed_generation_policy.generate_event(self.last_state,
                                                                          self.last_event,
                                                                          self.current_state,
                                                                          is_script_activated=self.is_script_activated,
                                                                          script_activated_event=self.script_activated_event)
            else:
                self.random_monkey_gui_exploration_event_count = 0
                self.seed_test_cnt += 1  # create a new test id
                self.seed_test_next_id += 1

                # disconnect the logcat at the end of test
                self.device.logcat.disconnect()

                # dump the coverage data at the end of test (i.e., before restart the app)
                if self.dump_coverage_mode:
                    try:
                        remote_coverage_data_file_path = "/data/data/" + self.app.get_package_name() + "/files/coverage.ec"
                        local_coverage_data_file_path = self.current_seed_test.test_output_dir
                        self.device.dump_coverage(remote_coverage_data_file_path, local_coverage_data_file_path)
                    except subprocess.CalledProcessError as e:
                        print("the error was caught !!!")
                        print(e.output)

                event = RestartEvent(self.app.get_start_intent(), self.app.get_package_name(),
                                     self.device.get_granted_runtime_permissions())

                if self.seed_test_cnt >= self.max_seed_test_suite_size:
                    event = None

        #  update the last state and event
        self.last_state = self.current_state
        self.last_event = event
        return event

    def update_utg_during_random_seed_generation(self):
        """
        Update the utg during the random seed generation phase (if the seed tests witness new UI pages)

            Since there is time difference between the event execution and model construction, the state right after the
               event may change itself (especially when the app has some dynamic feature, e.g., a notification bar may
               disappear after a few seconds).

            If these cases happen, we will update the event log's old to_state to the new to_state.

            Based on this consideration, we update the original utg and the utg of test at the same time, this could
               keep the consistency.

            Note we deep.deepcopy for some states since we do not want mess up with the original utg's states
                and the seed test's states. Here, we deeopcopy all states from the event logs.
            
           :return:
        """
        if self.current_state.state_str != self.last_event_log.to_state.state_str:
            # Update the utg if the current state is different from the to state

            # We update the event log before model construction if the current state is different from the to_state
            self.last_event_log.update_to_state_of_event_log(self.current_state, self.device.output_dir)

            #######################################
            # update the original utg
            #######################################
            if self.enable_update_original_utg:
                # deepcopy the to_state
                tmp_to_state = DeviceState.deepcopy_device_state(self.last_event_log.to_state, self.device)

                assert (
                        self.last_event_log.event_log_json_file_path is not None
                ), "[Random Seed Generation] event_log_json_file_path cannot be None"

                self.original_utg.add_transition(self.last_event,
                                                 self.last_state,
                                                 tmp_to_state,
                                                 event_log_file_path=self.last_event_log.event_log_json_file_path,
                                                 event_views_file_path=self.last_event_log.event_views_file_path,
                                                 remove_self_loop_transition=False)

            #######################################
            # update the utg of seed test
            #######################################
            tmp_last_state = DeviceState.deepcopy_device_state(self.last_state, self.device)
            # tmp_current_state = DeviceState.deepcopy_device_state(self.current_state, self.device)

            assert (
                    self.last_event_log.event_log_json_file_path is not None
            ), "[Random Seed Generation] event_log_json_file_path cannot be None"

            # update the utg of seed test
            self.current_seed_test.utg.add_utg_transition_for_gui_test(self.last_event,
                                                                       tmp_last_state,
                                                                       self.last_event_log.to_state,
                                                                       event_log_file_path=self.last_event_log.event_log_json_file_path,
                                                                       event_views_file_path=self.last_event_log.event_views_file_path,
                                                                       utg_output_dir=self.current_seed_test.test_output_dir,
                                                                       gui_test_tag=TEST_TAG_SEED_TEST,
                                                                       insert_start_position=self.current_seed_test.insert_start_position,
                                                                       independent_trace_len=self.current_seed_test.independent_trace_len)

        else:

            #######################################
            # update the original utg
            #######################################
            if self.enable_update_original_utg:
                assert (
                        self.last_event_log.event_log_json_file_path is not None
                ), "[Random Seed Generation] event_log_json_file_path cannot be None"

                # update the original utg
                self.original_utg.add_transition(self.last_event,
                                                 self.last_state,
                                                 self.current_state,
                                                 event_log_file_path=self.last_event_log.event_log_json_file_path,
                                                 event_views_file_path=self.last_event_log.event_views_file_path,
                                                 remove_self_loop_transition=False)

            #######################################
            # update the utg of seed test
            #######################################

            assert (
                    self.last_event_log.event_log_json_file_path is not None
            ), "[Random Seed Generation] event_log_json_file_path cannot be None"

            self.current_seed_test.utg.add_utg_transition_for_gui_test(self.last_event,
                                                                       DeviceState.deepcopy_device_state(
                                                                           self.last_state, self.device),
                                                                       self.last_event_log.to_state,
                                                                       event_log_file_path=self.last_event_log.event_log_json_file_path,
                                                                       event_views_file_path=self.last_event_log.event_views_file_path,
                                                                       utg_output_dir=self.current_seed_test.test_output_dir,
                                                                       gui_test_tag=TEST_TAG_SEED_TEST,
                                                                       insert_start_position=self.current_seed_test.insert_start_position,
                                                                       independent_trace_len=self.current_seed_test.independent_trace_len)

    def concretize_model_based_random_seed_tests(self, current_state: DeviceState):

        self.logger.info("Current state: %s" % current_state.state_str)

        event = self.get_next_event(current_state)

        return event

    def get_next_event(self, current_state: DeviceState):
        """
        get the next event to concretize
        :param current_state:
        :return:
        """

        if self.model_based_seed_test_index < len(self.model_based_random_seed_tests):

            # get the current "seed" test
            seed_test = self.model_based_random_seed_tests[self.model_based_seed_test_index]

            if self.model_based_seed_test_event_index < len(seed_test):

                # get the event of "seed" test
                event_dict = seed_test[self.model_based_seed_test_event_index]

                # TODO original code, need to uncomment
                event = event_dict['event']
                # find the original from_state of this event
                from_state_of_event = self.original_utg.get_node_by_state_str(
                    event_dict['original_utg_from_state_str'])
                # TODO END

                # # TODO need to be removed, just for debugging
                # event_id = event_dict['id']
                # original_utg_event_dict = None
                # event = None
                # from_state_str = None
                # for (start_state_str, end_state_str) in self.original_utg.G.edges:
                #     events = self.original_utg.G[start_state_str][end_state_str]['events']
                #     for event_str in events:
                #         if events[event_str]['id'] == event_id:
                #             original_utg_event_dict = events[event_str]
                #             event = events[event_str]['event']
                #             from_state_str = start_state_str
                #             break
                # from_state_of_event = self.original_utg.get_node_by_state_str(from_state_str)
                # # TODO End

                views_of_event = event.get_views()
                view_of_event = views_of_event[0] if len(views_of_event) >= 1 else None

                if view_of_event is not None:

                    # Find the matched views (from the current state) of view_of_event that belongs to from_state
                    matched_views, found_exact_match = current_state.locate_matched_views(view_of_event,
                                                                                          from_state_of_event,
                                                                                          self.config_script)

                    if len(matched_views) == 0:

                        # If we cannot find a matched view, this may indicate the event is broken at this point,
                        #   them we stop.
                        self.logger.warning("Cannot find any matched view, "
                                            "the test is not replayable at this operation, skip this event ...")

                        # get the unreplayable seed test prefix
                        utg_event_ids = self.current_seed_test.utg_event_ids_of_test + [event_dict['id']]
                        trie_prefix = ""
                        for i in utg_event_ids:
                            trie_prefix += "/" + str(i)
                        self.unreplayable_test_prefix_set.add(trie_prefix)

                        # switch to next seed test event
                        self.model_based_seed_test_event_index += 1
                        # return NOPEvent() if we fail to find any matched view
                        return NOPEvent()

                    else:
                        # update the view of event if we find a matched view
                        view_of_most_matched = matched_views[0]
                        event.set_views([view_of_most_matched])
                else:
                    # The view could be None if the event is of KeyEvent.
                    #   We will just execute such events.
                    pass

                # switch to next event if the current event ends
                self.model_based_seed_test_event_index += 1
                self.current_seed_test.add_utg_event_id(event_dict['id'])
                return event

            else:

                # check next seed test when the current seed test is replayed
                while True:
                    # switch to next seed test if the current test ends
                    self.model_based_seed_test_index += 1
                    self.model_based_seed_test_event_index = 0

                    if self.model_based_seed_test_index < len(self.model_based_random_seed_tests):
                        # additional check
                        next_seed_test = self.model_based_random_seed_tests[self.model_based_seed_test_index]
                        utg_event_ids = [event_dict['id'] for event_dict in next_seed_test]
                        trie_prefix = ""
                        for i in utg_event_ids:
                            trie_prefix += "/" + str(i)
                        if trie_prefix in self.unreplayable_test_prefix_set:
                            # continue if this seed test is not replayable
                            self.logger.info("skip this seed test, doomed to be not replayable.")
                            continue
                        else:
                            # break if this seed test is not in the trie
                            break
                    else:
                        # break if no model-based seed tests are available
                        break

                return None
        else:
            return None

    def __monkey_based_random_gui_exploration(self, current_state):
        """
        We randomly explore GUI pages like Google Monkey to generate GUI tests
        :param current_state:
        :return:
        """

        self.logger.info("Current state: %s" % current_state.state_str)
        if current_state.state_str in self.__missed_states:
            self.__missed_states.remove(current_state.state_str)

        if current_state.get_app_activity_depth(self.app) < 0:
            # If the app is not in the activity stack
            start_app_intent = self.app.get_start_intent()

            # It seems the app stucks at some state, has been
            # 1) force stopped (START, STOP)
            #    just start the app again by increasing self.__num_restarts
            # 2) started at least once and cannot be started (START)
            #    pass to let viewclient deal with this case
            # 3) nothing
            #    a normal start. clear self.__num_restarts.

            if self.__event_trace.endswith(EVENT_FLAG_START_APP + EVENT_FLAG_STOP_APP) \
                    or self.__event_trace.endswith(EVENT_FLAG_START_APP):
                self.__num_restarts += 1
                self.logger.info("The app had been restarted %d times.", self.__num_restarts)
            else:
                self.__num_restarts = 0

            # pass (START) through
            if not self.__event_trace.endswith(EVENT_FLAG_START_APP):
                # Start the app
                self.__event_trace += EVENT_FLAG_START_APP
                self.logger.info("Trying to start the app...")
                return IntentEvent(intent=start_app_intent)

        elif current_state.get_app_activity_depth(self.app) > 0:
            # If the app is in activity stack but is not in foreground
            self.__num_steps_outside += 1

            if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE:
                # If the app has not been in foreground for too long, try to go back
                if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE_KILL:
                    stop_app_intent = self.app.get_stop_intent()
                    go_back_event = IntentEvent(stop_app_intent)
                else:
                    go_back_event = KeyEvent(name="BACK")
                self.__event_trace += EVENT_FLAG_NAVIGATE
                self.logger.info("Going back to the app...")
                return go_back_event
        else:
            # If the app is in foreground
            self.__num_steps_outside = 0

        touch_events = []  # include TouchEvent and SetTextEvent
        long_touch_events = []
        navigation_events = []

        pct_touch_event = 60.0
        pct_long_touch_event = 35.0
        pct_navigation_event = 5.0

        # Get all possible input events
        possible_events = current_state.get_possible_input(ignore_windows_script=self.ignore_windows_script)
        for event in possible_events:
            if type(event) is TouchEvent or type(event) is SetTextEvent:
                touch_events.append(event)
            elif type(event) is LongTouchEvent:
                long_touch_events.append(event)
            elif type(event) is ScrollEvent:
                navigation_events.append(event)
            else:
                pass

        # add "BACK" as a navigation event
        navigation_events.append(KeyEvent(name="BACK"))

        event = None

        # round-robin of selecting events according to pct until we get an event
        while event is None:
            rand_pct = random.randint(0, 100)
            if 0 <= rand_pct <= pct_touch_event:
                self.__event_trace += EVENT_FLAG_EXPLORE
                event = UtgBasedPropertyFuzzingPolicy.random_event(touch_events)
            elif pct_touch_event < rand_pct <= pct_touch_event + pct_long_touch_event:
                self.__event_trace += EVENT_FLAG_EXPLORE
                event = UtgBasedPropertyFuzzingPolicy.random_event(long_touch_events)
            else:
                self.__event_trace += EVENT_FLAG_NAVIGATE
                event = UtgBasedPropertyFuzzingPolicy.random_event(navigation_events)
            if event is not None:
                break
        return event

    @staticmethod
    def random_event(events):
        """
        randomly select an event
        :param events:
        :return: None, if the event list is empty
        """
        if len(events) == 0:
            return None
        else:
            rand_index = random.randint(0, len(events) - 1)
            return events[rand_index]

    def load_existing_offline_seed_tests(self):
        """
        load existing offline seed tests generated by online test generation strategies

        This method can be used for offline debugging.
        :return:
        """
        assert os.path.exists(self.seed_tests_dir), 'No seed tests exist! Please generate seed tests first!!'

        seed_ids_to_mutate = set()  # e.g., "seed-test-1"
        if self.seeds_to_mutate != 'all':
            for i in self.seeds_to_mutate.strip(';').split(';'):
                seed_ids_to_mutate.add('seed-test-{}'.format(int(i)))
            print("only mutate seed test: %s" % seed_ids_to_mutate)

        # get the list of seed test dirs
        seed_dirs = sorted([os.path.join(self.seed_tests_dir, x)
                            for x in next(os.walk(self.seed_tests_dir))[1]])

        # collect the events in each seed test dir
        for seed_dir in seed_dirs:

            if self.seeds_to_mutate != 'all' and os.path.basename(seed_dir) not in seed_ids_to_mutate:
                continue

            gui_test_case = GUITestCase(self.device, self.app, self.random_input,
                                        test_output_dir=seed_dir,
                                        test_tag=TEST_TAG_SEED_TEST).recover_test_case()

            if gui_test_case is None:
                self.logger.warning("recover %d failed!" % seed_dir)
                continue

            seed_test_id = gui_test_case.test_id

            # add the seed test
            if seed_test_id not in self.seed_tests:
                self.seed_tests[seed_test_id] = gui_test_case

    def start(self, input_manager):
        """
        Totally override the "start" method in the parent class to enable customization
        See this link for more info about python class overriding:
            https://www.thedigitalcatonline.com/blog/2014/05/19/method-overriding-in-python/
        :param input_manager:
        :return:
        """
        assert self.mode_check

        if self.mode_gen or self.mode_gen_seeds or self.mode_gen_mutants:
            try:
                # add exception handling
                self.original_utg.recover_original_utg(self.utg_dir)  # recover the utg
            except Exception as e:
                self.logger.error("recover the original utg failed!!!")
                self.logger.error(e)
                return

            if self.mode_gen or self.mode_gen_seeds:

                if self.seed_test_generation_strategy == UtgBasedPropertyFuzzingPolicy.MONKEY_RANDOM_SEED_GENERATION:

                    self.generate_random_seed_tests(input_manager, self.seed_test_generation_strategy)

                    if self.seed_test_generation_exception:
                        # stop if some exceptions happen in seed test generation
                        return
                    pass

                elif self.seed_test_generation_strategy == UtgBasedPropertyFuzzingPolicy.MODEL_BASED_RANDOM_SEED_GENERATION:
                    # TODO we now do not use this mode

                    # cluster the original utg
                    self.clustered_utg.cluster_utg_structure(self.original_utg)

                    # generate model based seed tests
                    self.model_based_random_seed_tests = \
                        self.generate_model_based_random_seed_tests(self.clustered_utg,
                                                                    self.max_random_seed_test_length,
                                                                    self.max_seed_test_suite_size)

                    self.generate_random_seed_tests(input_manager, self.seed_test_generation_strategy)

                    if self.seed_test_generation_exception:
                        # stop if some exceptions happen in seed test generation
                        return

        if self.mode_gen_mutants:
            # load the generated seed tests directly from files
            self.load_existing_offline_seed_tests()

        # We cluster the original utg at this time since we want to integrate the possible new states/events
        #   witnessed during seed generation.
        self.clustered_utg.cluster_utg_structure(self.original_utg)

        if self.mode_gen or self.mode_gen_mutants:
            # do mutant generation

            self.map_seed_tests_to_clustered_utg()

            self.identify_active_views()
            self.generate_mutant_tests()

    def map_seed_tests_to_clustered_utg(self):
        """
        Map the seed tests to the clustered utg
        (1) we can get the clustered utg event ids
        :return:
        """

        for seed_test_id in self.seed_tests:
            # get the seed test
            seed_test = self.seed_tests[seed_test_id]

            utg_event_ids_of_seed_test, _ = seed_test.get_utg_event_ids_on_clustered_utg(self.clustered_utg)

            seed_test.add_utg_event_ids(utg_event_ids_of_seed_test)

            print("seed test's utg ids: " + str(seed_test.utg_event_ids_of_test))

    def identify_active_views(self):
        """
        Identify the active views in the seed tests
        :return:
        """
        for test_id in self.seed_tests:
            self.logger.info("identify active views in the seed test: " + test_id)
            self.current_seed_test = self.seed_tests[test_id]
            event_logs = self.current_seed_test.event_logs

            history_states = []
            for i in range(0, len(event_logs)):
                print("update active views for (state_id: %d, event_id: %d)" % (i, i + 1))
                event_log = event_logs[i]
                from_state = event_log.from_state
                history_states.append(from_state)
                # all the states before the from state (Note this creates a new list from history_states)
                prev_states = history_states[:(len(history_states) - 1)]
                self.annotate_active_view(event_log, from_state, prev_states)

    def annotate_active_view(self, event_log: EventLog, current_state: DeviceState, prev_states: List[DeviceState]):
        """
        Annotate the view of input event as active on the current state where the event was fired, and update the
        active views from a previous, comparable state to the current state.

        Note that we only need to update the active views from the first previous, comparable state, because we already
        updated the active views from *more previous* states to this first previous state.

        :param event_log: the event log of input event
        :param current_state: the state where the input event was fired
        :param prev_states: the states that have been witnessed before the current state.
                    These history states will be used to update their active views onto the current state if possible.
        :return:
        """

        # The two operations are order-sensitive:
        #   (1) update the previous active views to the current state
        #   (2) update the active view on the current state
        #   This avoids the active view on the current state is overwritten by previous active views in the same
        #        independent region.
        #   Fix #32

        # Step 1: update the previous active views to the current state
        # (in-place) reverse the states
        prev_states.reverse()
        for i in range(0, len(prev_states)):
            prev_state = prev_states[i]
            if current_state.is_activity_different_from(prev_state):
                # skip the state if it has different foreground activity with the current state
                # a.k.a they must be different (100% precise)
                continue
            elif not current_state.is_different_from(prev_state):
                # Condition: the two states have the same activity and same state_str
                # When the current state is totally identical to one previous state,
                #   we do not need to do any update.
                #   Because they are the same object in the memory (same utg node) (~100% precise)
                print("matched with state id [%d]" % (len(prev_states) - i - 1))
                break
            elif DeviceState.are_comparable_states(current_state, prev_state, self.config_script):
                # Condition: the two states have the same activity but are not exact same.
                # Possible reasons:
                #   (1) the window stacks are different, i.e. totally structurally different.
                #   (2) the window stacks are same, but
                #       GUI pages are different
                #          (e.g., the main activity view and its drawer view)
                #       OR,
                #       list of views and their properties are different
                #          (e,g, some text changed? some new widgets appear? some previous widgets disappear?)

                # update the active view info if their structures are identical (not 100% precise)
                print("matched with state id [%d]" % (len(prev_states) - i - 1))
                current_state.update_active_views_from_prev_comparable_state(prev_state)

                break
            else:

                pass

        # Step2: Get the independent views
        # Note: this step should be executed before Step 3 so that we can still emit the same event of the current
        #   event_log. The reason is that the independent traces are inserted before this event log.
        event_log.independent_views = current_state.get_all_independent_views()

        # Step 3: update the active view on the current state
        input_event = event_log.event
        views = input_event.get_views()
        target_view = views[0] if len(views) >= 1 else None
        if target_view is not None:
            # annotate the active view if the event manipulate some view
            # Some input events may not directly work on some view, but we still should update the active view later on.
            current_state.annotate_active_view(target_view)

    def run_mutant_with_seed(self, mutant_test: GUITestCase, seed_test: GUITestCase, do_oracle_checking=True):

        self.logger.info("Run " + mutant_test.test_id)

        # Step 1: clean the test's previous data if exists before the execution
        mutant_test.clean_mutant_data(clean_oracle_data=True, clean_runtime_data=True)

        # Step 2: run the test
        self.run_test(mutant_test)

        # Step 3: check execution status
        has_crash, crash_confidence = self.__check_crash_error()
        mutant_test.has_crash = has_crash
        mutant_test.crash_confidence = crash_confidence
        mutant_test.dump_execution_status(seed_test)

        # Step 4: do semantic checking
        if do_oracle_checking:
            mutant_test.do_oracle_checking(seed_test, config_script=self.config_script)

            current_datetime = datetime.datetime.now()
            test_execution_result = "[" + str(current_datetime) + "]" \
                                    + "seed test: " + str(seed_test.test_id) \
                                    + ", mutant test: " + str(mutant_test.test_id) \
                                    + ", has crash?: " + str(mutant_test.has_crash) \
                                    + ", has semantic error?: " + str(mutant_test.has_semantic_error) + "\n"

            self.logger.info("\n\n" + test_execution_result + "\n\n")

    def generate_mutant_tests(self):
        """
        mutate the seed tests
        :return:
        """
        assert (self.mode_gen or self.mode_gen_mutants)

        self.current_seed_test = None

        for seed_test_id, seed_test in self.seed_tests.items():
            self.mutate_seed_test(self.seed_tests[seed_test_id])

    def mutate_seed_test(self, seed_test: GUITestCase):

        assert (self.mode_gen or self.mode_gen_mutants)

        event_logs_of_seed_test: List[EventLog] = seed_test.event_logs
        # map EventLog to the cluster utg
        for event_log in event_logs_of_seed_test:
            event_log.map_to_cluster_utg()

        total_number_of_mutants_per_seed_test = 0

        # Eqv. to #insertion positions
        event_logs_len: int = len(event_logs_of_seed_test)

        if self.mutant_gen_n is True:
            # create one thread for each insertion position
            n = event_logs_len
        elif self.mutant_gen_n is False:
            n = 1
        else:
            assert isinstance(self.mutant_gen_n, int)
            n = self.mutant_gen_n

        with ThreadPool(n) as p:
            for insert_position in range(event_logs_len):
                p.apply_async(self.mutant_generation_wrapper, args=(seed_test, insert_position,),
                              callback=print, error_callback=print)

            p.close()
            p.join()

    def find_top_n_similar_states(self, target_state: DeviceState, top_n=1):
        """
        Find top #N similar states
        :param target_state: the target state
        :param top_n: number of similar states
        :return:
        """

        target_state_plain_str = target_state.get_content_free_state_plain_str()
        # Tuple(state_similarity_ratio, state)
        similar_states: List[Tuple[float, DeviceState]] = []

        for structure_str in self.clustered_utg.G.nodes():
            state: DeviceState = self.clustered_utg.G.nodes[structure_str]['state']
            if state.foreground_activity == target_state.foreground_activity and \
                    target_state.structure_str != structure_str:
                # make sure the two states are different on the clustered utg but have the same foreground activity
                state_plain_str = state.get_content_free_state_plain_str()
                similarity_ratio = Levenshtein.ratio(target_state_plain_str, state_plain_str)
                similar_states.append((similarity_ratio, state))

        # sort the similar states from most similar to least similar
        similar_states = sorted(similar_states, key=lambda x: x[0], reverse=True)

        # get the top N similar states
        top_n_similar_states: List[DeviceState] = []
        cnt = 0
        for (ratio, state) in similar_states:
            if cnt < top_n:
                self.logger.info("the state similarity ratio: %f" % ratio)
                top_n_similar_states.append(state)
                cnt += 1
            else:
                break

        return top_n_similar_states

    def mutant_generation_wrapper(self, seed_test, insertion_position):

        thread_data = threading.local()
        # init the mutant test id for each seed test
        thread_data.mutant_test_id = 0

        # record all inserted independent traces for one seed test's each insertion position
        log_file_path_of_inserted_independent_traces = os.path.join(seed_test.test_output_dir,
                                                                    "seed_mutation_at_insertion_position_["
                                                                    + str(insertion_position) +
                                                                    "]_" + strftime("%Y-%m%d-%H%M%-S"))

        event_logs_of_seed_test: List[EventLog] = seed_test.event_logs

        # insert "independent(noop) trace" at each position of seed test
        event_log = event_logs_of_seed_test[insertion_position]

        # Get the independent events
        independent_events: List[str] = []
        from_state: DeviceState = event_log.from_state
        for independent_view_id in event_log.independent_views:
            independent_view = from_state.views[independent_view_id]
            independent_events.append(DeviceState.get_view_property_values(independent_view))

        # find similar states from most similar to least similar
        #   Some preliminary observation: the number of mutants increases linearly with top_n
        most_similar_states = self.find_top_n_similar_states(from_state, top_n=2)

        total_number_of_mutants_per_insertion_position = 0

        # find independent event traces that starts from from_state
        number_of_mutants = self.find_independent_event_trace_loops(
            from_state, [from_state] + most_similar_states,
            thread_data,
            seed_test=seed_test,
            insertion_position=insertion_position,
            independent_events=independent_events,
            max_independent_trace_length=self.max_independent_trace_length,
            max_number_of_mutants_per_insertion_position=self.max_mutants_per_insertion_position,
            log_file_path_of_inserted_independent_traces=log_file_path_of_inserted_independent_traces)

        total_number_of_mutants_per_insertion_position += number_of_mutants

        # Experimental strategy
        if total_number_of_mutants_per_insertion_position < self.max_mutants_per_insertion_position:
            # find more independent event trace "loops" that starts from most similar states
            #   if we still have budgets

            for state in most_similar_states:

                number_of_mutants = self.find_independent_event_trace_loops(
                    state, [from_state] + most_similar_states,
                    thread_data,
                    seed_test=seed_test,
                    insertion_position=insertion_position,
                    independent_events=independent_events,
                    max_independent_trace_length=self.max_independent_trace_length,
                    max_number_of_mutants_per_insertion_position=self.max_mutants_per_insertion_position,
                    log_file_path_of_inserted_independent_traces=log_file_path_of_inserted_independent_traces)

                total_number_of_mutants_per_insertion_position += number_of_mutants

                if not (total_number_of_mutants_per_insertion_position < self.max_mutants_per_insertion_position):
                    break

        return total_number_of_mutants_per_insertion_position

    def find_independent_event_trace_loops(self, source_state, target_states: List[DeviceState],
                                           thread_data: threading.local,
                                           seed_test=None, insertion_position=None, independent_events=None,
                                           max_independent_trace_length=None,
                                           max_number_of_mutants_per_insertion_position=None,
                                           log_file_path_of_inserted_independent_traces=None):
        """
        Find independent event traces that starts from a given source_state and ends at a given set of target_states.
         These event traces should be within a given trace length, and will be added into the seed test at specific
         insertion_position to generate the corresponding mutant tests.

         Note:

         1. The first event (locates in the source_state) can only be selected from the given set of independent
         events (i.e., these independent events of this set are supposed to not affect prior events in the seed test
         w.r.t the GUI effect). For the remaining events, we now do not put any constraints.

         2. One typical scenario is source_state and target_states are the same state. In this case, we find event trace
         loops w.r.t a specific state (which is one state of the seed test).

         However, the clustered utg may have limitations, e.g., (1) we may not be able to construct a complete model, i.e.,
         one each GUI page, we may not be able to click each possible events. (2) our abstract strategy to get the
         clustered utg may not be good enough (too fine-grained).

         Thus, to cover more search space and overcome the clustered utg's limitation, we also choose similar states
         w.r.t source_state as source_state and target_states (coarse-grained).

         3. We now use breadth-first search to find the event trace loops.

            Other search strategies, e.g., depth-first search, may also work.
                https://eddmann.com/posts/depth-first-search-and-breadth-first-search-in-python/

        :param source_state: the source state to start the search of independent event trace
        :param target_states: the target states to end the search
        :param seed_test: the seed test
        :param insertion_position: the insertion position of an independent trace in the seed test
        :param independent_events: the independent events that can be selected from the source state of the seed test
        :param max_independent_trace_length: the maximum length of any generated independent traces
        :param max_number_of_mutants_per_insertion_position: the maximum number of generated independent traces
        :param log_file_path_of_inserted_independent_traces: log file name
        :return: int, number of generated mutants
        """

        print("========Generate Mutants (seed test: %s, insert position: %s) ==========="
              % (seed_test.test_id, str(insertion_position)))

        # find the source state on the clustered utg
        source_state_structure_str = source_state.structure_str
        if source_state_structure_str not in self.clustered_utg.G.nodes:
            # ensure the source state is indeed on the clustered utg
            return 0

        # find the target states on the clustered utg
        target_state_structure_strs: List[str] = []
        for target_state in target_states:
            tmp_structure_str = target_state.structure_str
            if tmp_structure_str not in self.clustered_utg.G.nodes:
                return 0
            target_state_structure_strs.append(tmp_structure_str)

        # the stack that records our research results
        #   data structure:
        #       str, state's structure_str
        #       List[EventLog], event logs (independent event trace) to be inserted
        #       List[int], utg event ids that corresponds to the event logs to be inserted
        #       List[Tuple], tuple of utg event id and its from_state's and to_state's structure_strs that
        #                    corresponds to the event logs to be inserted.
        stack: List[Tuple[str, List[EventLog], List[int], List[Tuple[str, int, str]]]] = \
            [(source_state_structure_str, [], [], [])]

        # the set to avoid valid but duplicate event traces
        #   Set(Tuple(int, int, ...))
        valid_paths_of_event_id = set()
        iteration = 1
        max_iteration = 1000

        while stack:

            iteration += 1
            if iteration > max_iteration:
                # Hot fix: stop after 10K tries for one insertion position
                print("Give up this insertion position after %d tries" % max_iteration)
                break

            if len(stack) == 0 or len(valid_paths_of_event_id) >= max_number_of_mutants_per_insertion_position:
                # the stack is empty or we found enough independent traces
                break

            # Breadth-first Random Search with Optimization
            candidate_traces_with_shortest_trace_len = []
            shortest_trace_length = 1000
            for i in range(0, len(stack)):
                node_structure_str, _, utg_event_ids_of_independent_trace, _ = stack[i]
                current_trace_length = len(utg_event_ids_of_independent_trace)
                if current_trace_length < shortest_trace_length:
                    shortest_trace_length = current_trace_length
                    candidate_traces_with_shortest_trace_len.clear()
                    candidate_traces_with_shortest_trace_len.append(i)
                elif current_trace_length == shortest_trace_length:
                    candidate_traces_with_shortest_trace_len.append(i)
                else:
                    # current_trace_length < longest_trace_length
                    pass

            # debug
            # print("--- Print candidate traces with shortest trace length ---")
            # for i in candidate_traces_with_shortest_trace_len:
            #     node_structure_str, _, utg_event_ids_of_independent_trace, _ = stack[i]
            #     print(utg_event_ids_of_independent_trace)
            # print("--- End")

            random_index = \
                candidate_traces_with_shortest_trace_len[
                    random.randint(0, len(candidate_traces_with_shortest_trace_len) - 1)
                ]
            stack_element = stack.pop(random_index)
            node_structure_str, event_logs_of_independent_trace, utg_event_ids_of_independent_trace, edges_of_path = \
                stack_element
            # End of Breadth-first Random Search

            # Depth-first Search
            # node_structure_str, event_logs_of_independent_trace, utg_event_ids_of_independent_trace, \
            #     edges_of_path = stack.pop()
            # End of Depth-first Search

            # self.logger.info(
            #     "the start page (%s), the current path pop out of stack: %a" %
            #     (node_structure_str, utg_event_ids_of_independent_trace))

            for next_node_structure_str in self.clustered_utg.G[node_structure_str]:

                if len(event_logs_of_independent_trace) > max_independent_trace_length:
                    # stop the search if the path exceeds the length bound
                    break

                # Optimization I: prune mutants if self-loop events appears more than two times
                if len(utg_event_ids_of_independent_trace) >= 2 and \
                        (utg_event_ids_of_independent_trace[-1] == utg_event_ids_of_independent_trace[-2]):
                    break

                # Optimization II: prune mutants if it contains more than three different self-loop events
                #  from the same state.
                bounded_cnt = max_independent_trace_length if max_independent_trace_length < 3 else 3
                if len(utg_event_ids_of_independent_trace) >= bounded_cnt and \
                        self.is_continuous_self_loop_events(edges_of_path[-bounded_cnt:]):
                    break

                # TODO need to be removed, this is just for debugging
                # ids_of_path_str = ""
                # for i in utg_event_ids_of_independent_trace:
                #     ids_of_path_str += str(i)
                #
                # if len(utg_event_ids_of_independent_trace) >= 1 and utg_event_ids_of_independent_trace[0] != 6:
                #    break
                # TODO END

                if (node_structure_str in target_state_structure_strs) and len(event_logs_of_independent_trace) != 0:
                    # 1. make sure the path reaches one of target states and is non-empty

                    tuple_of_ids_of_path = tuple(utg_event_ids_of_independent_trace)
                    if tuple_of_ids_of_path not in valid_paths_of_event_id:
                        # 2. make sure the path is a new and unique valid path

                        # 3. make sure the independent trace if inserted is aligned with the seed test.
                        #  For example, assume the seed test is S1 -(e1)-> S2 -(e2)-> S3, the insertion position is 1
                        #  (i.e., the independent trace will be inserted before e2 and after S2), and the independent
                        #   trace is Sx -(ex)-> Sy, and thus the mutant test will be like:
                        #         S1 -(e1)-> S2 "-(ex)-> Sy" -(e2)-> S3
                        #   So we need to check the alignment in two aspects:
                        #   (1) is e2 contained in Sy?
                        #   (2) is ex contained in S2?

                        # get the input event right after the insertion position in the seed test
                        input_event_after_insertion_position = seed_test.get_input_event_from_test_by_index(
                            insertion_position)
                        # get the concrete target state
                        target_state: DeviceState = self.clustered_utg.G.nodes[node_structure_str]['state']
                        if not target_state.contain_input_event(input_event_after_insertion_position):
                            # Is ex contained in S2? i.e., check whether the event of the seed test after the insertion
                            #   position is contained in the target state
                            break

                        # get the first input event of the independent event trace
                        first_input_event_of_independent_trace = event_logs_of_independent_trace[0].event
                        # get the concrete state right before the insertion position
                        from_state_before_insertion_position: DeviceState = seed_test.get_from_state_from_test_by_index(
                            insertion_position)
                        if not from_state_before_insertion_position.contain_input_event(
                                first_input_event_of_independent_trace):
                            # Is ex contained in S2? i.e., check whether the first event of the independent trace is
                            #   contained in the from_state before the insertion position
                            break

                        # record the path if it satisfies the above three conditions
                        print("seed (%s), insert_position (%d), #mutant (%d), the valid inserted trace: %s"
                              % (seed_test.test_id,
                                 insertion_position,
                                 len(valid_paths_of_event_id) + 1,
                                 str(tuple_of_ids_of_path)))

                        # We construct the mutant test and dump it into the file system, and do not put the mutant
                        #   test in memory. This avoids OutOfMemoryException.
                        mutant_test = self.create_mutant_test(seed_test,
                                                              insertion_position,
                                                              event_logs_of_independent_trace,
                                                              utg_event_ids_of_independent_trace, thread_data)

                        if mutant_test is None:
                            break

                        if not self.parallel_run_mode:
                            self.log_independent_event_trace(log_file_path_of_inserted_independent_traces,
                                                             seed_test, insertion_position, tuple_of_ids_of_path,
                                                             mutant_test, source_state_structure_str)

                        # run the mutant test immediately when it was created
                        if self.mode_run:

                            try:

                                self.run_mutant_with_seed(mutant_test, seed_test)

                            except CurrentStateNoneException as e:
                                self.logger.warning(
                                    "mutant test: [%s] execution failed!" % str(mutant_test.test_id))
                                self.logger.warning("the current state is None: %s" % e)
                            except Exception as e:
                                self.logger.warning(
                                    "mutant test: [%s] execution failed!" % str(mutant_test.test_id))
                                self.logger.warning("exception in executing the mutant test: %s" % e)
                                import traceback
                                traceback.print_exc()

                        valid_paths_of_event_id.add(tuple_of_ids_of_path)

                # exhaustive enumeration
                events = self.clustered_utg.G[node_structure_str][next_node_structure_str]['events']
                for (event_str, event_dict) in list(events.items()):
                    # Here, we have not used copy.deepycopy on from_state and end_state when creating EventLog
                    #  We think it will not bring any side effect, because
                    #  (1) from_state and end_state will not be modified later on, thus self.clustered_utg
                    #       will not be affected
                    #  (2) these event logs will be copy.deepcopy when creating mutant tests

                    # get the event and its id
                    input_event: InputEvent = event_dict['event']
                    input_event_id = event_dict['id']
                    event_log_json_file_path = event_dict['event_log_file_path']
                    event_views_file_path = event_dict['event_views_file_path']

                    # get the event log's from_state and to_state from the original utg
                    from_state = self.original_utg.G.nodes[event_dict['original_utg_from_state_str']]['state']
                    to_state = self.original_utg.G.nodes[event_dict['original_utg_to_state_str']]['state']
                    # create the event log
                    event_log = EventLog(self.device, self.app, input_event,
                                         profiling_method=None, tag=None,
                                         event_str=input_event.get_event_str(from_state),
                                         event_log_json_file_path=event_log_json_file_path,
                                         event_views_file_path=event_views_file_path,
                                         from_state=from_state, to_state=to_state)

                    if len(event_logs_of_independent_trace) == 0:
                        # Only select independent views at the first insertion point
                        views = event_log.event.get_views()
                        target_view = views[0] if len(views) >= 1 else None
                        if target_view is not None:
                            # Check whether the current view corresponds to an independent event
                            view_property_str = DeviceState.get_view_property_values(target_view)
                            if view_property_str in independent_events:
                                stack.append((next_node_structure_str,
                                              event_logs_of_independent_trace + [event_log],
                                              utg_event_ids_of_independent_trace + [input_event_id],
                                              edges_of_path +
                                              [(node_structure_str, input_event_id, next_node_structure_str)]))

                    else:
                        # any views can be selected after the first insertion step
                        stack.append((next_node_structure_str,
                                      event_logs_of_independent_trace + [event_log],
                                      utg_event_ids_of_independent_trace + [input_event_id],
                                      edges_of_path +
                                      [(node_structure_str, input_event_id, next_node_structure_str)]))

        return len(valid_paths_of_event_id)

    def __is_self_loop_event(self, utg_edge):
        """
        check whether the utg edge corresponds to a self-loop event
        :return:
        """
        start_state_structure_str = utg_edge[0]
        end_state_structure_str = utg_edge[2]
        if start_state_structure_str == end_state_structure_str:
            return True
        else:
            return False

    def is_continuous_self_loop_events(self, utg_edges: List):
        """
        check whether the given utg edges corresponds to self-loop events on the same utg node
        :param utg_edges:
        :return:
        """
        if len(utg_edges) == 0:
            return False

        for edge in utg_edges:
            if not self.__is_self_loop_event(edge):
                return False

        state_structure_str = utg_edges[0][0]
        for edge in utg_edges[1:]:
            if not (state_structure_str == edge[0]):
                return False

        return True

    def log_independent_event_trace(self, log_file_path, seed_test: GUITestCase, insert_position, tuple_of_ids_of_path,
                                    mutant_test: GUITestCase, source_state_structure_str):

        log_file = open(log_file_path, "a+")
        current_datetime = datetime.datetime.now()

        # represent the mutant test in the form of utg event ids
        mutant_test_in_utg_event_ids = "["
        for i in range(0, len(seed_test.utg_event_ids_of_test)):
            if i != 0:
                mutant_test_in_utg_event_ids += ","
            if i == insert_position:
                # add the inserted independent trace before the insertion position
                mutant_test_in_utg_event_ids += str(tuple_of_ids_of_path) + ","
                mutant_test_in_utg_event_ids += "*" + \
                                                str(seed_test.utg_event_ids_of_test[i]) + \
                                                "*"
            else:
                mutant_test_in_utg_event_ids += str(seed_test.utg_event_ids_of_test[i])
        mutant_test_in_utg_event_ids += "]"

        # dump the mutant test in the form of utg event ids
        mutant_inserted_trace = "[" + str(current_datetime) + ", " + \
                                str(seed_test.test_id) + ", " + \
                                "pivot state: " + source_state_structure_str + ", " + \
                                "insert position: " + str(insert_position) + "," + \
                                str(mutant_test.test_id) + \
                                "]" + " insert indpendent trace: " + str(tuple_of_ids_of_path) \
                                + "\n\t" + \
                                " mutant test in utg event ids: " + \
                                mutant_test_in_utg_event_ids + "\n\n"

        log_file.write(mutant_inserted_trace)
        log_file.close()

    #
    def create_mutant_test(self, seed_test: GUITestCase, insert_position, event_logs_of_independent_trace,
                           utg_event_ids_of_independent_trace, thread_data: threading.local):
        """
        dump the mutant test into file system
        :param seed_test:
        :param insert_position:
        :param event_logs_of_independent_trace:
        :param utg_event_ids_of_independent_trace:
        :param thread_data:
        :return:
        """

        # check whether this test is not replayable
        tmp_utg_event_ids = list(seed_test.utg_event_ids_of_test)
        tmp_utg_event_ids[insert_position:insert_position] = utg_event_ids_of_independent_trace
        if not self.parallel_run_mode:
            trie_prefix = ""
            for i in tmp_utg_event_ids:
                trie_prefix += "/" + str(i)
            if trie_prefix in self.unreplayable_test_prefix_set:
                print("the mutant test is unreplayable, prune it !")
                return None

        # get the seed test's event logs
        event_logs_of_seed_test = seed_test.event_logs

        # create new event logs for each mutant test
        event_logs_of_mutant_test: List[EventLog] = copy.deepcopy(event_logs_of_seed_test)

        for iel in event_logs_of_independent_trace:
            # add the color tag for each new event log
            iel.set_color_tag(COLOR_BLUE)
            iel.set_insertion_tag(True)

        # construct the mutant by combining the event logs of seed test and independent trace
        event_logs_of_mutant_test[insert_position:insert_position] = event_logs_of_independent_trace

        # recover device, app, logger after deepcopy
        for event_log in event_logs_of_mutant_test:
            event_log.recover_after_deepcopy(self.device, self.app)
            event_log.from_state.recover_after_deep_copy(self.device)
            event_log.to_state.recover_after_deep_copy(self.device)

        # create the mutated GUI test
        thread_data.mutant_test_id += 1
        mutant_test_id = "mutant-" + str(insert_position) + "-" + str(thread_data.mutant_test_id)
        mutant_test_output_dir = os.path.join(seed_test.test_output_dir, mutant_test_id)
        mutant_test = GUITestCase(self.device, self.app, self.random_input,
                                  test_id=mutant_test_id,
                                  test_output_dir=mutant_test_output_dir,
                                  test_tag=TEST_TAG_MUTANT_TEST)
        # update the event logs and insert position
        mutant_test.add_event_logs(event_logs_of_mutant_test)
        mutant_test.set_insert_position(insert_position, len(event_logs_of_independent_trace))

        # update the path of utg event ids
        mutant_test.add_utg_event_ids(tmp_utg_event_ids)

        # construct the utg of mutant test before execution
        mutant_test.construct_test_utg_based_on_event_logs()
        # integrate the seed test's utg with mutant's utg
        mutant_test.merge_with_another_test(seed_test)

        return mutant_test

    def run_test(self, mutant_test: GUITestCase):
        """
        run a single mutant test
        :param mutant_test: GUITestCase
        :return:
        """
        if mutant_test is None:
            return

        # Prepare the execution env for the mutant test
        # 1. Execute FRESH_RESTART event before executing each mutant test
        fresh_restart_event = RestartEvent(self.app.get_start_intent(), self.app.get_package_name(),
                                           self.device.get_granted_runtime_permissions())
        fresh_restart_event.send(self.device)

        # 2. Record the current state right after FRESH_RESTART
        while True:
            current_state = self.device.get_current_state(mutant_test.test_output_dir)
            if current_state is not None:
                break

        # 3. Restart logcat
        self.device.logcat.reconnect(self.app.package_name, mutant_test.logcat_file)

        # 4. Set the input event cnt of mutant's utg as ZERO (only for visualization purpose)
        mutant_test.utg.input_event_count = 0

        # 5. Start to execute the mutant test
        # the event logs with statically generated event sequences
        event_logs: List[EventLog] = mutant_test.event_logs
        # the event logs that are dynamically executed, which will update the mutant test's event logs later
        dynamic_event_logs: List[EventLog] = []

        for i in range(len(event_logs)):

            event_log = event_logs[i]
            event = event_log.event  # get the input event
            print("to execute event id %d" % (i + 1))

            # We need to find a matched view for any events after the insertion point
            # We can safely execute the events before the insertion point
            if i >= mutant_test.get_insert_start_position():

                views_of_event = event.get_views()
                view_of_event = views_of_event[0] if len(views_of_event) >= 1 else None

                if view_of_event is not None:

                    # Find the matched views of view_of_event that belongs to event_log.from_state
                    matched_views, found_exactly_matched_view = \
                        current_state.locate_matched_views(view_of_event, event_log.from_state)

                    if len(matched_views) == 0:

                        # If we cannot find a matched view, this may indicate the mutant is broken at this point,
                        #  and then record the mutant as not replayable, and stop the execution
                        self.logger.warning("the test cannot be fully replayed, give up ...")

                        mutant_test.is_fully_replayed = False
                        mutant_test.unreplayable_event_log_index = i
                        mutant_test.unreplayable_utg_event_ids_prefix = mutant_test.utg_event_ids_of_test[0:(i + 1)]

                        if not self.parallel_run_mode:
                            # add the unreplayable test prefix into the trie structure
                            unreplayable_test_prefix = mutant_test.convert_utg_event_ids_to_trie_prefix(
                                event_id_index=i)
                            self.unreplayable_test_prefix_set.add(unreplayable_test_prefix)

                        break

                    else:

                        if not found_exactly_matched_view:
                            # set the mutant test is not faithfully replayed
                            mutant_test.is_faithfully_replayed = False

                            # TODO [for debugging] annotate the not exactly matched views
                            # not_exactly_matched_views_dir = os.path.join(mutant_test.output_dir, "unmatched_views")
                            # if not os.path.exists(not_exactly_matched_views_dir):
                            #     os.makedirs(not_exactly_matched_views_dir)
                            # # annotate the original view intended for exactly matching
                            # new_screenshot_path = os.path.join(not_exactly_matched_views_dir, "original-view-"
                            #                                    + str(i) + ".png")
                            # event_log.from_state.annotate_view_on_screenshot(event_log.from_state.screenshot_path,
                            #                                                  new_screenshot_path,
                            #                                                  [view_of_event],
                            #                                                  COLOR_RED_TUPLE)
                            #
                            # # annotate the approximately matched on the current state
                            # new_screenshot_path = os.path.join(not_exactly_matched_views_dir, "approx-matched-views-"
                            #                                    + str(i) + ".png")
                            # current_state.annotate_view_on_screenshot(current_state.screenshot_path,
                            #                                           new_screenshot_path,
                            #                                           matched_views,
                            #                                           COLOR_BLUE_TUPLE)

                        # update the view of event if we find a matched view
                        view_of_most_matched = matched_views[0]
                        event.set_views([view_of_most_matched])
                else:
                    # The view could be None if the event is of NOPEvent or KeyEvent.
                    # We will just execute such events.
                    pass

            # Create a new event log
            event_log = EventLog(self.device, self.app, event,
                                 utg_event_id=mutant_test.utg.input_event_count + 1,
                                 is_inserted_event=event_log.is_inserted_event)
            # Execute the event log, which will update its runtime from_state and to_state
            event_log.run(mutant_test.test_output_dir, event_interval=self.event_interval)

            print("----")

            # update the dynamic event logs
            dynamic_event_logs.append(event_log)

            # get the current state
            while True:
                current_state = self.device.get_current_state(mutant_test.test_output_dir)
                if current_state is not None:
                    break

            # Note we do not include NOPEvent from the seed test into the mutant test's utg
            if current_state.state_str != event_log.to_state.state_str:
                # update to_state
                event_log.update_to_state_of_event_log(current_state, mutant_test.test_output_dir)

            # update the mutant test's utg
            mutant_test.utg.add_utg_transition_for_gui_test(event_log.event,
                                                            event_log.from_state,
                                                            event_log.to_state,
                                                            event_log_file_path=event_log.event_log_json_file_path,
                                                            event_views_file_path=event_log.event_views_file_path,
                                                            utg_output_dir=mutant_test.test_output_dir,
                                                            gui_test_tag=TEST_TAG_DYNAMIC_TEST,
                                                            is_inserted_event=event_log.is_inserted_event,
                                                            insert_start_position=mutant_test.insert_start_position,
                                                            independent_trace_len=mutant_test.independent_trace_len,
                                                            utg_event_ids_of_test=mutant_test.utg_event_ids_of_test,
                                                            output_utg=True)

            # TODO just for debugging, can be removed
            # print("from_state (%s) -> to_state (%s)" %
            # (event_log.from_state.state_str, event_log.to_state.state_str))

        # Clean up after the execution of mutant test
        # 1. disconnect the logcat
        self.device.logcat.disconnect()
        # 2. update the mutant's event logs
        mutant_test.event_logs = dynamic_event_logs
        # 3. dump the coverage data before restart the app
        if self.dump_coverage_mode:
            try:
                remote_coverage_data_file_path = "/data/data/" + self.app.get_package_name() + "/files/coverage.ec"
                local_coverage_data_file_path = mutant_test.test_output_dir
                self.device.dump_coverage(remote_coverage_data_file_path, local_coverage_data_file_path)
            except subprocess.CalledProcessError as e:
                self.logger.warning("An error when collecting coverage data !!!")
                self.logger.warning(e.output)

        return

    def __check_crash_error(self):
        if self.device.logcat.check_crash():
            confidence = self.device.logcat.get_crash_confidence()
            return True, confidence
        else:
            return False, ""


class RunMutantPolicy(UtgBasedPropertyFuzzingPolicy):
    def __init__(self, device, app, config_script, event_interval=0, mutant_dir=None, seed_of_mutant=None,
                 do_oracle_checking=False, dump_coverage_mode=False):

        assert mutant_dir is not None and os.path.exists(mutant_dir)

        self.mode = 'run'

        super().__init__(device, app, None, config_script, False, event_interval=event_interval,
                         dump_coverage_mode=dump_coverage_mode)

        self.enable_parallel_mode = True
        self.do_oracle_checking = do_oracle_checking

        # used when run mutated test
        self.mutant_dir = mutant_dir
        self.seed_of_mutant = seed_of_mutant if seed_of_mutant is not None \
            else os.path.dirname(os.path.abspath(self.mutant_dir))

    def start(self, input_manager):

        assert self.mode_only_run and not self.mode_gen and not self.mode_gen_seeds and not self.mode_gen_mutants

        # recover seed test and mutant test from the file system
        mutant_test = GUITestCase(self.device, self.app, self.random_input,
                                  test_output_dir=self.mutant_dir,
                                  test_tag=TEST_TAG_MUTANT_TEST).recover_test_case(overwrite=True)
        seed_test = GUITestCase(self.device, self.app, self.random_input,
                                test_output_dir=self.seed_of_mutant,
                                test_tag=TEST_TAG_SEED_TEST).recover_test_case()

        mutant_test.merge_with_another_test(seed_test)

        if mutant_test is None or seed_test is None:
            self.logger.warning('recovered mutant test {} or seed test {} failed'.format(mutant_test, seed_test))
            return

        try:

            self.run_mutant_with_seed(mutant_test, seed_test, do_oracle_checking=self.do_oracle_checking)

        except CurrentStateNoneException as e:
            self.logger.warning(
                "mutant test: [%s] execution failed!" % str(mutant_test.test_id))
            self.logger.warning("the current state is None: %s" % e)

        except Exception as e:
            self.logger.warning("mutant test: [%s] execution failed!" % str(mutant_test.test_id))
            self.logger.warning("exception in executing the mutant test: %s" % e)
            import traceback
            traceback.print_exc()


class UtgBasedInputPolicy(InputPolicy):
    """
    state-based input policy
    """

    def __init__(self, device, app, random_input):
        super(UtgBasedInputPolicy, self).__init__(device, app)
        self.random_input = random_input
        self.script = None
        self.master = None
        self.script_events = []
        self.last_event = None
        #  add a flag to record where the event come from, which decides the following state type
        self.last_event_type = None
        # End
        self.last_state = None
        self.current_state = None
        self.utg = UTG(device=device, app=app, random_input=random_input)
        self.script_event_idx = 0
        if self.device.humanoid is not None:
            self.humanoid_view_trees = []
            self.humanoid_events = []

        #  the default setting is True
        self.enable_update_utg = True

        # the flag that indicates whether the script is activated
        self.is_script_activated = False
        self.script_activated_event = None

    def generate_event(self):
        """
        generate an event
        @return:
        """

        # print("before get state: %s" % datetime.datetime.now())
        # Get current device state (be careful, when assigning self.current_state, which maintains a lot of information)
        self.current_state = self.device.get_current_state(self.device.output_dir)
        if self.current_state is None:
            #  If cannot get the current state, BACK
            time.sleep(5)
            return KeyEvent(name="BACK")
        # print("after get state: %s" % datetime.datetime.now())

        #  record the execution path
        # self.utg.record_execution_path(self.last_event, self.last_event_type, self.last_state, self.current_state)

        # print("before utg: %s" % datetime.datetime.now())
        #  update utg
        if self.enable_update_utg:
            self.__update_utg()
        # print("after utg: %s" % datetime.datetime.now())

        # update last view trees for humanoid
        if self.device.humanoid is not None:
            self.humanoid_view_trees = self.humanoid_view_trees + [self.current_state.view_tree]
            if len(self.humanoid_view_trees) > 4:
                self.humanoid_view_trees = self.humanoid_view_trees[1:]

        event = None
        event_type = None

        # if the previous operation is not finished, continue
        if len(self.script_events) > self.script_event_idx:
            #  debug
            print("if the previous operation is not finished, continue ...")
            event = self.script_events[self.script_event_idx].get_transformed_event(self)
            if event is None:
                self.logger.warning('script do not match view, stop sending script events')
                self.script_events = []
                self.script_event_idx = 0
            else:
                self.script_event_idx += 1
            #
            event_type = EVENT_TYPE_SCRIPT

        # First try matching a state defined in the script
        if event is None and self.script is not None:
            #  debug
            # print("First try matching a state defined in the script ...")
            operation = self.script.get_operation_based_on_state(self.current_state)
            if operation is not None:
                self.script_events = operation.events
                # restart script
                event = self.script_events[0].get_transformed_event(self)
                self.script_event_idx = 1
                #
                event_type = EVENT_TYPE_SCRIPT

                # record which event triggers the script
                self.is_script_activated = True
                self.script_activated_event = self.last_event

        #  generate an event from the UTG
        if event is None:
            event = self.generate_event_based_on_utg()
            #
            event_type = EVENT_TYPE_EXPLORE

        # update last events for humanoid
        if self.device.humanoid is not None:
            self.humanoid_events = self.humanoid_events + [event]
            if len(self.humanoid_events) > 3:
                self.humanoid_events = self.humanoid_events[1:]

        #  update the last state and event
        self.last_state = self.current_state
        self.last_event = event

        # TODO can be removed, just for debugging
        # if self.last_event is not None:
        #     views_of_last_event = self.last_event.get_views()
        #     view_of_last_event = views_of_last_event[0] if len(views_of_last_event) >= 1 else None
        #     if view_of_last_event is not None:
        #         view_id = view_of_last_event['temp_id']
        #         view_str = view_of_last_event['view_str']
        #
        #         for view in self.last_state.views:
        #             if view['view_str'] == view_str:
        #                 if view['temp_id'] != view_id:
        #                     self.logger.error("inconsistent found!!!")
        #                     assert False

        self.last_event_type = event_type
        return event

    def __update_utg(self):
        """
        Since there is time difference between the event execution and model construction, the state right after the
            event could change itself (especially when the app has some dynamic feature, e.g., a notification bar).

        If these cases happen, we will update the event log's old to_state to the new to_state.

        This consideration could make the utg model more consistent.
        :return:
        """
        if self.current_state.state_str != self.last_event_log.to_state.state_str:
            # update the event log's original to_state by the new to_state before model construction
            #   if the current state is different from the to_state
            self.last_event_log.update_to_state_of_event_log(self.current_state, self.device.output_dir)

        # TODO just for debugging, can be removed
        # with open(self.last_event_log.event_log_json_file_path, "r") as f:
        #     try:
        #         # event_dict is in the form of EventLog
        #         event_log_dict = json.load(f)
        #     except Exception as e:
        #         self.logger.info("Loading %s failed:  %s" % (self.last_event_log.event_log_json_file_path, e))
        #         raise Exception
        #
        #     start_state_str = event_log_dict["start_state"]
        #     stop_state_str = event_log_dict["stop_state"]
        #     if self.last_state is not None and self.last_event_log.to_state is not None:
        #         if start_state_str != self.last_state.state_str and stop_state_str != self.last_event_log.to_state.state_str:
        #             raise Exception("Validation Failed! Event log file was not correctly created!!!")

        assert (
                self.last_event_log.event_log_json_file_path is not None
        ), "[Model Construction] event_log_json_file_path cannot be None"

        self.utg.add_transition(self.last_event, self.last_state,
                                self.current_state,  # the same as "self.last_event_log.to_state"
                                event_log_file_path=self.last_event_log.event_log_json_file_path,
                                event_views_file_path=self.last_event_log.event_views_file_path)

        # TODO just for debugging, can be removed
        # if self.last_event is not None:
        #     views_of_last_event = self.last_event.get_views()
        #     view_of_last_event = views_of_last_event[0] if len(views_of_last_event) >= 1 else None
        #     if view_of_last_event is not None:
        #         view_id = view_of_last_event['temp_id']
        #         view_str = view_of_last_event['view_str']
        #
        #         for view in self.last_state.views:
        #             if view['view_str'] == view_str:
        #                 if view['temp_id'] != view_id:
        #                     self.logger.error("inconsistent found!!!")
        #                     assert False

    @abstractmethod
    def generate_event_based_on_utg(self):
        """
        generate an event based on UTG
        :return: InputEvent
        """
        pass


class WeightedSearchPolicy(UtgBasedInputPolicy):
    """
        a new search policy according to an input event's weight
    """

    def __init__(self, device, app, random_input, search_method, ignore_windows_script=None, restart_threshold=None):
        super(WeightedSearchPolicy, self).__init__(device, app, random_input)

        # random seed generation policy
        self.weighted_model_exploration_policy = \
            WeightedRandomExplorationPolicy(
                device,
                app,
                random_input,
                search_method=search_method,
                ignore_windows_script=ignore_windows_script)

    def generate_event_based_on_utg(self):
        # Now, we use weighted random seed test generation
        event = self.weighted_model_exploration_policy.generate_event(self.last_state,
                                                                      self.last_event,
                                                                      self.current_state,
                                                                      is_script_activated=self.is_script_activated,
                                                                      script_activated_event=self.script_activated_event)

        return event


class UtgNaiveSearchPolicy(UtgBasedInputPolicy):
    """
    depth-first strategy to explore UFG (old)
    """

    def __init__(self, device, app, random_input, search_method):
        super(UtgNaiveSearchPolicy, self).__init__(device, app, random_input)
        self.logger = logging.getLogger(self.__class__.__name__)

        self.explored_views = set()
        self.state_transitions = set()
        self.search_method = search_method

        self.last_event_flag = ""
        self.last_event_str = None
        self.last_state = None

        self.preferred_buttons = ["yes", "ok", "activate", "detail", "more", "access",
                                  "allow", "check", "agree", "try", "go", "next"]

    def generate_event_based_on_utg(self):
        """
        generate an event based on current device state
        note: ensure these fields are properly maintained in each transaction:
          last_event_flag, last_touched_view, last_state, exploited_views, state_transitions
        @return: InputEvent
        """
        self.save_state_transition(self.last_event_str, self.last_state, self.current_state)

        if self.device.is_foreground(self.app):
            # the app is in foreground, clear last_event_flag
            self.last_event_flag = EVENT_FLAG_STARTED
        else:
            number_of_starts = self.last_event_flag.count(EVENT_FLAG_START_APP)
            # If we have tried too many times but the app is still not started, stop DroidBot
            if number_of_starts > MAX_NUM_RESTARTS:
                raise InputInterruptedException("The app cannot be started.")

            # if app is not started, try start it
            if self.last_event_flag.endswith(EVENT_FLAG_START_APP):
                # It seems the app stuck at some state, and cannot be started
                # just pass to let viewclient deal with this case
                self.logger.info("The app had been restarted %d times.", number_of_starts)
                self.logger.info("Trying to restart app...")
                pass
            else:
                start_app_intent = self.app.get_start_intent()

                self.last_event_flag += EVENT_FLAG_START_APP
                self.last_event_str = EVENT_FLAG_START_APP
                return IntentEvent(start_app_intent)

        # select a view to click
        view_to_touch = self.select_a_view(self.current_state)

        # if no view can be selected, restart the app
        if view_to_touch is None:
            stop_app_intent = self.app.get_stop_intent()
            self.last_event_flag += EVENT_FLAG_STOP_APP
            self.last_event_str = EVENT_FLAG_STOP_APP
            return IntentEvent(stop_app_intent)

        view_to_touch_str = view_to_touch['view_str']
        if view_to_touch_str.startswith('BACK'):
            result = KeyEvent('BACK')
        else:
            result = TouchEvent(view=view_to_touch)

        self.last_event_flag += EVENT_FLAG_TOUCH
        self.last_event_str = view_to_touch_str
        self.save_explored_view(self.current_state, self.last_event_str)
        return result

    def select_a_view(self, state):
        """
        select a view in the view list of given state, let droidbot touch it
        @param state: DeviceState
        @return:
        """
        views = []
        for view in state.views:
            if view['enabled'] and len(view['children']) == 0:
                views.append(view)

        if self.random_input:
            random.shuffle(views)

        # add a "BACK" view, consider go back first/last according to search policy
        mock_view_back = {'view_str': 'BACK_%s' % state.foreground_activity,
                          'text': 'BACK_%s' % state.foreground_activity}
        if self.search_method == POLICY_NAIVE_DFS:
            views.append(mock_view_back)
        elif self.search_method == POLICY_NAIVE_BFS:
            views.insert(0, mock_view_back)

        # first try to find a preferable view
        for view in views:
            view_text = view['text'] if view['text'] is not None else ''
            view_text = view_text.lower().strip()
            if view_text in self.preferred_buttons \
                    and (state.foreground_activity, view['view_str']) not in self.explored_views:
                self.logger.info("selected an preferred view: %s" % view['view_str'])
                return view

        # try to find a un-clicked view
        for view in views:
            if (state.foreground_activity, view['view_str']) not in self.explored_views:
                self.logger.info("selected an un-clicked view: %s" % view['view_str'])
                return view

        # if all enabled views have been clicked, try jump to another activity by clicking one of state transitions
        if self.random_input:
            random.shuffle(views)
        transition_views = {transition[0] for transition in self.state_transitions}
        for view in views:
            if view['view_str'] in transition_views:
                self.logger.info("selected a transition view: %s" % view['view_str'])
                return view

        # no window transition found, just return a random view
        # view = views[0]
        # self.logger.info("selected a random view: %s" % view['view_str'])
        # return view

        # DroidBot stuck on current state, return None
        self.logger.info("no view could be selected in state: %s" % state.tag)
        return None

    def save_state_transition(self, event_str, old_state, new_state):
        """
        save the state transition
        @param event_str: str, representing the event cause the transition
        @param old_state: DeviceState
        @param new_state: DeviceState
        @return:
        """
        if event_str is None or old_state is None or new_state is None:
            return
        if new_state.is_different_from(old_state):
            self.state_transitions.add((event_str, old_state.tag, new_state.tag))

    def save_explored_view(self, state, view_str):
        """
        save the explored view
        @param state: DeviceState, where the view located
        @param view_str: str, representing a view
        @return:
        """
        if not state:
            return
        state_activity = state.foreground_activity
        self.explored_views.add((state_activity, view_str))


class UtgScriptSearchPolicy(UtgBasedInputPolicy):
    """
    This strategy operates as follows:
        1. If human scripts are available, replay the human scripts first
        2. Randomly explore UI pages
        3. Systematically explore UI pages
            DFS/BFS (according to search_method) strategy to explore UFG
    """

    MAX_EXPLORATION_EVENT = 10
    MAX_RANDOM_MONKEY_UTG_EXPLORATION_EVENT_CNT = 20

    def __init__(self, device, app, random_input, search_method):
        super(UtgScriptSearchPolicy, self).__init__(device, app, random_input)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.search_method = search_method

        self.preferred_buttons = ["yes", "ok", "activate", "detail", "more", "access",
                                  "allow", "check", "agree", "try", "go", "next"]

        self.__nav_target = None
        self.__nav_num_steps = -1
        self.__num_restarts = 0
        self.__num_steps_outside = 0
        self.__event_trace = ""
        self.__missed_states = set()
        self.__random_explore = False

        #
        self.human_script_replay_mode = True  # the flag indicating the human script replay mode
        self.enable_replay = False  # enable (start) the replay
        self.check_replay_state = False  # check states during replay
        self.replay_target_state = None  #  the target state for replaying
        self.path_events = []
        self.path_event_idx = 0
        self.path_states = []
        self.path_state_idx = 0

        self.random_monkey_utg_exploration_event_count = 0
        self.greedy_utg_exploration_event_count = 0

    def find_target_state(self):

        # get the states that are reachable from the entry state
        # NOTE TODO the reachable states are not in a specific order
        states_reachable_from_entry_state = self.utg.get_reachable_states_from_first_state()
        target_state = None
        for state in states_reachable_from_entry_state:
            # first choose a script state that has not been fully explored
            if state.is_script_state():
                if not self.utg.is_state_explored(state):
                    target_state = state
                    break

        if target_state is None:
            # If all script states are fully explored,
            # then choose a explore state that has not been fully explored
            for state in states_reachable_from_entry_state:
                if state.is_explore_state():
                    if not self.utg.is_state_explored(state):
                        target_state = state
                        break

        if target_state is None:
            # If all script and explore states are fully explored
            # then randomly choose one state
            cnt = len(states_reachable_from_entry_state)
            if cnt > 0:
                from random import randint
                rand_int = randint(0, cnt)
                target_state = states_reachable_from_entry_state[rand_int]

        return target_state

    def generate_event_based_on_utg(self):
        """
        generate an event based on current UTG
        We use script events to guide ui exploration. Three key variables to properly maintain:
        self.check_replay_state (control whether we will check the states when replaying script events),
        self.enable_replay (control the generation of script events),
        self.human_script_replay_mode (control the replay mode, we will generate a path events from utg for replaying)
        @return: InputEvent
        """

        # the event to be replayed or executed
        event = None

        if len(self.path_states) > self.path_state_idx and self.check_replay_state:
            # self.current_state = self.device.get_current_state()
            expected_state = self.path_states[self.path_state_idx]
            self.path_state_idx += 1
            # we check whether the replaying is successful or not along the path
            if self.current_state.is_structure_different_from(expected_state):
                self.logger.info("fail to replay the last event: %s, on the last state: %s" %
                                 (self.last_event, self.last_state))
            else:
                self.logger.info("successfully replay the last event: %s, on the last state: %s" %
                                 (self.last_event, self.last_state))
            # disable replay state checking if all path states have been checked
            if len(self.path_states) == self.path_state_idx:
                self.check_replay_state = False

        # if the previous operation is not finished, continue ...
        if len(self.path_events) > self.path_event_idx and self.enable_replay:
            print("replay the path events, continue ...")
            event = self.path_events[self.path_event_idx]
            self.path_event_idx += 1
            # disable utg construction during replaying
            self.enable_update_utg = False
            self.check_replay_state = True
            # disable replay if all path events have been emitted
            if len(self.path_events) == self.path_event_idx:
                self.enable_replay = False
            return event

        # If self.script is enabled, we first try to get the path events of the target state
        if event is None and self.script is not None and self.human_script_replay_mode:
            #  debug
            print("First try to get the path events of the target state ...")
            self.replay_target_state = self.find_target_state()
            if self.replay_target_state is None:
                # If couldn't find a exploration target, stop the app
                logging.error("cannot find a target state to build the utg, exit ...")
                stop_app_intent = self.app.get_stop_intent()
                self.logger.info("Cannot find an exploration target. Trying to restart app...")
                self.__event_trace += EVENT_FLAG_STOP_APP
                return IntentEvent(intent=stop_app_intent)

            path_events, path_states = self.replay_target_state.get_shortest_path_events()
            if path_events is not None:
                # assign the path events
                self.path_events = path_events
                self.path_event_idx = 0
                # assign the path states
                self.path_states = path_states
                self.path_state_idx = 0
                # disable utg construction during replaying
                self.enable_update_utg = False
                # enable the replace when we find a path
                self.human_script_replay_mode = False
                self.enable_replay = True
                self.__event_trace += EVENT_FLAG_FRESH_RESTART
                return RestartEvent(self.app.get_start_intent(), self.app.get_package_name(),
                                    self.device.get_granted_runtime_permissions())

        # Random GUI exploration mode
        if event is None:
            if self.random_monkey_utg_exploration_event_count < UtgScriptSearchPolicy.MAX_RANDOM_MONKEY_UTG_EXPLORATION_EVENT_CNT:
                event = self.__random_monkey_utg_exploration(self.current_state)
                # enable utg update if UI exploration mode is started
                self.enable_update_utg = True
                # increase event count
                self.random_monkey_utg_exploration_event_count += 1
                return event
            else:
                self.random_monkey_utg_exploration_event_count = 0
                # disable utg update
                self.enable_update_utg = False
                return RestartEvent(self.app.get_start_intent(), self.app.get_package_name(),
                                    self.device.get_granted_runtime_permissions())

        # Systematic GUI exploration mode
        if event is None:
            if self.greedy_utg_exploration_event_count < UtgScriptSearchPolicy.MAX_EXPLORATION_EVENT:
                event = self.__greedy_utg_exploration(self.current_state)
                # enable utg update if UI exploration mode is started
                self.enable_update_utg = True
                # increase event count
                self.greedy_utg_exploration_event_count += 1
                return event
            else:
                self.greedy_utg_exploration_event_count = 0
                # restart state selection
                self.human_script_replay_mode = True
                # disable utg update
                self.enable_update_utg = False
                return NOPEvent()

    @staticmethod
    def __random_event(events):
        """
        randomly select an event
        :param events:
        :return: None, if the event list is empty
        """
        if len(events) == 0:
            return None
        else:
            rand_index = random.randint(0, len(events) - 1)
            return events[rand_index]

    def __random_monkey_utg_exploration(self, current_state):
        """
        We randomly explore GUI pages like Google Monkey
        :param current_state:
        :return:
        """

        self.logger.info("Current state: %s" % current_state.state_str)
        if current_state.state_str in self.__missed_states:
            self.__missed_states.remove(current_state.state_str)

        if current_state.get_app_activity_depth(self.app) < 0:
            # If the app is not in the activity stack
            start_app_intent = self.app.get_start_intent()

            # It seems the app stucks at some state, has been
            # 1) force stopped (START, STOP)
            #    just start the app again by increasing self.__num_restarts
            # 2) started at least once and cannot be started (START)
            #    pass to let viewclient deal with this case
            # 3) nothing
            #    a normal start. clear self.__num_restarts.

            if self.__event_trace.endswith(EVENT_FLAG_START_APP + EVENT_FLAG_STOP_APP) \
                    or self.__event_trace.endswith(EVENT_FLAG_START_APP):
                self.__num_restarts += 1
                self.logger.info("The app had been restarted %d times.", self.__num_restarts)
            else:
                self.__num_restarts = 0

            # pass (START) through
            if not self.__event_trace.endswith(EVENT_FLAG_START_APP):
                # Start the app
                self.__event_trace += EVENT_FLAG_START_APP
                self.logger.info("Trying to start the app...")
                return IntentEvent(intent=start_app_intent)

        elif current_state.get_app_activity_depth(self.app) > 0:
            # If the app is in activity stack but is not in foreground
            self.__num_steps_outside += 1

            if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE:
                # If the app has not been in foreground for too long, try to go back
                if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE_KILL:
                    stop_app_intent = self.app.get_stop_intent()
                    go_back_event = IntentEvent(stop_app_intent)
                else:
                    go_back_event = KeyEvent(name="BACK")
                self.__event_trace += EVENT_FLAG_NAVIGATE
                self.logger.info("Going back to the app...")
                return go_back_event
        else:
            # If the app is in foreground
            self.__num_steps_outside = 0

        touch_events = []  # include TouchEvent and SetTextEvent
        long_touch_events = []
        navigation_events = []

        pct_touch_event = 60.0
        pct_long_touch_event = 35.0
        pct_navigation_event = 5.0

        # Get all possible input events
        possible_events = current_state.get_possible_input()
        for event in possible_events:
            if type(event) is TouchEvent or type(event) is SetTextEvent:
                touch_events.append(event)
            elif type(event) is LongTouchEvent:
                long_touch_events.append(event)
            elif type(event) is ScrollEvent:
                navigation_events.append(event)
            else:
                pass

        # add "BACK" as a navigation event
        navigation_events.append(KeyEvent(name="BACK"))

        event = None

        # round-robin of selecting events according to pct until we get an event
        while event is None:

            rand_pct = random.randint(0, 100)
            if 0 <= rand_pct <= pct_touch_event:
                self.__event_trace += EVENT_FLAG_EXPLORE
                event = self.__random_event(touch_events)
            elif pct_touch_event < rand_pct <= pct_touch_event + pct_long_touch_event:
                self.__event_trace += EVENT_FLAG_EXPLORE
                event = self.__random_event(long_touch_events)
            else:
                self.__event_trace += EVENT_FLAG_NAVIGATE
                event = self.__random_event(navigation_events)

            if event is not None:
                break

        return event

    def __greedy_utg_exploration(self, current_state):

        self.logger.info("Current state: %s" % current_state.state_str)
        if current_state.state_str in self.__missed_states:
            self.__missed_states.remove(current_state.state_str)

        if current_state.get_app_activity_depth(self.app) < 0:
            # If the app is not in the activity stack
            start_app_intent = self.app.get_start_intent()

            # It seems the app stucks at some state, has been
            # 1) force stopped (START, STOP)
            #    just start the app again by increasing self.__num_restarts
            # 2) started at least once and cannot be started (START)
            #    pass to let viewclient deal with this case
            # 3) nothing
            #    a normal start. clear self.__num_restarts.

            if self.__event_trace.endswith(EVENT_FLAG_START_APP + EVENT_FLAG_STOP_APP) \
                    or self.__event_trace.endswith(EVENT_FLAG_START_APP):
                self.__num_restarts += 1
                self.logger.info("The app had been restarted %d times.", self.__num_restarts)
            else:
                self.__num_restarts = 0

            # pass (START) through
            if not self.__event_trace.endswith(EVENT_FLAG_START_APP):
                if self.__num_restarts > MAX_NUM_RESTARTS:
                    # If the app had been restarted too many times, enter random mode
                    msg = "The app had been restarted too many times. Entering random mode."
                    self.logger.info(msg)
                    self.__random_explore = True
                else:
                    # Start the app
                    self.__event_trace += EVENT_FLAG_START_APP
                    self.logger.info("Trying to start the app...")
                    return IntentEvent(intent=start_app_intent)

        elif current_state.get_app_activity_depth(self.app) > 0:
            # If the app is in activity stack but is not in foreground
            self.__num_steps_outside += 1

            if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE:
                # If the app has not been in foreground for too long, try to go back
                if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE_KILL:
                    stop_app_intent = self.app.get_stop_intent()
                    go_back_event = IntentEvent(stop_app_intent)
                else:
                    go_back_event = KeyEvent(name="BACK")
                self.__event_trace += EVENT_FLAG_NAVIGATE
                self.logger.info("Going back to the app...")
                return go_back_event
        else:
            # If the app is in foreground
            self.__num_steps_outside = 0

        # Get all possible input events
        possible_events = current_state.get_possible_input()

        # TODO  we can shuffle the events according to their weights
        if self.random_input:
            random.shuffle(possible_events)

        if self.search_method == POLICY_GREEDY_DFS:
            possible_events.append(KeyEvent(name="BACK"))
        elif self.search_method == POLICY_GREEDY_BFS:
            possible_events.insert(0, KeyEvent(name="BACK"))

        # get humanoid result, use the result to sort possible events
        # including back events
        if self.device.humanoid is not None:
            possible_events = self.__sort_inputs_by_humanoid(possible_events)

        # If there is an unexplored event, try the event first
        for input_event in possible_events:
            if not self.utg.is_event_explored(event=input_event, state=current_state):
                self.logger.info("Trying an unexplored event.")
                self.__event_trace += EVENT_FLAG_EXPLORE
                return input_event

        target_state = self.__get_nav_target(current_state)
        if target_state:
            event_path = self.utg.get_event_path(current_state=current_state, target_state=target_state)
            if event_path and len(event_path) > 0:
                self.logger.info("Navigating to %s, %d steps left." % (target_state.state_str, len(event_path)))
                self.__event_trace += EVENT_FLAG_NAVIGATE
                return event_path[0]

        if self.__random_explore:
            self.logger.info("Trying random event.")
            random.shuffle(possible_events)
            return possible_events[0]

        # If couldn't find a exploration target, stop the app
        stop_app_intent = self.app.get_stop_intent()
        self.logger.info("Cannot find an exploration target. Trying to restart app...")
        self.__event_trace += EVENT_FLAG_STOP_APP
        return IntentEvent(intent=stop_app_intent)

    def __sort_inputs_by_humanoid(self, possible_events):
        if sys.version.startswith("3"):
            from xmlrpc.client import ServerProxy
        else:
            from xmlrpclib import ServerProxy
        proxy = ServerProxy("http://%s/" % self.device.humanoid)
        request_json = {
            "history_view_trees": self.humanoid_view_trees,
            "history_events": [x.__dict__ for x in self.humanoid_events],
            "possible_events": [x.__dict__ for x in possible_events],
            "screen_res": [self.device.display_info["width"],
                           self.device.display_info["height"]]
        }
        result = json.loads(proxy.predict(json.dumps(request_json)))
        new_idx = result["indices"]
        text = result["text"]
        new_events = []

        # get rid of infinite recursive by randomizing first event
        if not self.utg.is_state_reached(self.current_state):
            new_first = random.randint(0, len(new_idx) - 1)
            new_idx[0], new_idx[new_first] = new_idx[new_first], new_idx[0]

        for idx in new_idx:
            if isinstance(possible_events[idx], SetTextEvent):
                possible_events[idx].text = text
            new_events.append(possible_events[idx])
        return new_events

    def __get_nav_target(self, current_state):
        # If last event is a navigation event
        if self.__nav_target and self.__event_trace.endswith(EVENT_FLAG_NAVIGATE):
            event_path = self.utg.get_event_path(current_state=current_state, target_state=self.__nav_target)
            if event_path and 0 < len(event_path) <= self.__nav_num_steps:
                # If last navigation was successful, use current nav target
                self.__nav_num_steps = len(event_path)
                return self.__nav_target
            else:
                # If last navigation was failed, add nav target to missing states
                self.__missed_states.add(self.__nav_target.state_str)

        reachable_states = self.utg.get_reachable_states(current_state)
        if self.random_input:
            random.shuffle(reachable_states)

        for state in reachable_states:
            # Only consider foreground states
            if state.get_app_activity_depth(self.app) != 0:
                continue
            # Do not consider missed states
            if state.state_str in self.__missed_states:
                continue
            # Do not consider explored states
            if self.utg.is_state_explored(state):
                continue
            self.__nav_target = state
            event_path = self.utg.get_event_path(current_state=current_state, target_state=self.__nav_target)
            if len(event_path) > 0:
                self.__nav_num_steps = len(event_path)
                return state

        self.__nav_target = None
        self.__nav_num_steps = -1
        return None


class UtgGreedySearchPolicy(UtgBasedInputPolicy):
    """
    DFS/BFS (according to search_method) strategy to explore UFG (new)
    """

    def __init__(self, device, app, random_input, search_method):
        super(UtgGreedySearchPolicy, self).__init__(device, app, random_input)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.search_method = search_method

        self.preferred_buttons = ["yes", "ok", "activate", "detail", "more", "access",
                                  "allow", "check", "agree", "try", "go", "next"]

        self.__nav_target = None
        self.__nav_num_steps = -1
        self.__num_restarts = 0
        self.__num_steps_outside = 0
        self.__event_trace = ""
        self.__missed_states = set()
        self.__random_explore = False

    def generate_event_based_on_utg(self):
        """
        generate an event based on current UTG
        @return: InputEvent
        """
        current_state = self.current_state
        self.logger.info("Current state: %s" % current_state.state_str)
        if current_state.state_str in self.__missed_states:
            self.__missed_states.remove(current_state.state_str)

        if current_state.get_app_activity_depth(self.app) < 0:
            # If the app is not in the activity stack
            start_app_intent = self.app.get_start_intent()

            # It seems the app stucks at some state, has been
            # 1) force stopped (START, STOP)
            #    just start the app again by increasing self.__num_restarts
            # 2) started at least once and cannot be started (START)
            #    pass to let viewclient deal with this case
            # 3) nothing
            #    a normal start. clear self.__num_restarts.

            if self.__event_trace.endswith(EVENT_FLAG_START_APP + EVENT_FLAG_STOP_APP) \
                    or self.__event_trace.endswith(EVENT_FLAG_START_APP):
                self.__num_restarts += 1
                self.logger.info("The app had been restarted %d times.", self.__num_restarts)
            else:
                self.__num_restarts = 0

            # pass (START) through
            if not self.__event_trace.endswith(EVENT_FLAG_START_APP):
                if self.__num_restarts > MAX_NUM_RESTARTS:
                    # If the app had been restarted too many times, enter random mode
                    msg = "The app had been restarted too many times. Entering random mode."
                    self.logger.info(msg)
                    self.__random_explore = True
                else:
                    # Start the app
                    self.__event_trace += EVENT_FLAG_START_APP
                    self.logger.info("Trying to start the app...")
                    return IntentEvent(intent=start_app_intent)

        elif current_state.get_app_activity_depth(self.app) > 0:
            # If the app is in activity stack but is not in foreground
            self.__num_steps_outside += 1

            if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE:
                # If the app has not been in foreground for too long, try to go back
                if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE_KILL:
                    stop_app_intent = self.app.get_stop_intent()
                    go_back_event = IntentEvent(stop_app_intent)
                else:
                    go_back_event = KeyEvent(name="BACK")
                self.__event_trace += EVENT_FLAG_NAVIGATE
                self.logger.info("Going back to the app...")
                return go_back_event
        else:
            # If the app is in foreground
            self.__num_steps_outside = 0

        # Get all possible input events
        possible_events = current_state.get_possible_input()

        # TODO  we can shuffle the events according to their weights
        if self.random_input:
            random.shuffle(possible_events)

        if self.search_method == POLICY_GREEDY_DFS:
            possible_events.append(KeyEvent(name="BACK"))
        elif self.search_method == POLICY_GREEDY_BFS:
            possible_events.insert(0, KeyEvent(name="BACK"))

        # get humanoid result, use the result to sort possible events
        # including back events
        if self.device.humanoid is not None:
            possible_events = self.__sort_inputs_by_humanoid(possible_events)

        # If there is an unexplored event, try the event first
        for input_event in possible_events:
            if not self.utg.is_event_explored(event=input_event, state=current_state):
                self.logger.info("Trying an unexplored event.")
                self.__event_trace += EVENT_FLAG_EXPLORE
                return input_event

        target_state = self.__get_nav_target(current_state)
        if target_state:
            event_path = self.utg.get_event_path(current_state=current_state, target_state=target_state)
            if event_path and len(event_path) > 0:
                self.logger.info("Navigating to %s, %d steps left." % (target_state.state_str, len(event_path)))
                self.__event_trace += EVENT_FLAG_NAVIGATE
                return event_path[0]

        if self.__random_explore:
            self.logger.info("Trying random event.")
            random.shuffle(possible_events)
            return possible_events[0]

        # If couldn't find a exploration target, stop the app
        stop_app_intent = self.app.get_stop_intent()
        self.logger.info("Cannot find an exploration target. Trying to restart app...")
        self.__event_trace += EVENT_FLAG_STOP_APP
        return IntentEvent(intent=stop_app_intent)

    def __sort_inputs_by_humanoid(self, possible_events):
        if sys.version.startswith("3"):
            from xmlrpc.client import ServerProxy
        else:
            from xmlrpclib import ServerProxy
        proxy = ServerProxy("http://%s/" % self.device.humanoid)
        request_json = {
            "history_view_trees": self.humanoid_view_trees,
            "history_events": [x.__dict__ for x in self.humanoid_events],
            "possible_events": [x.__dict__ for x in possible_events],
            "screen_res": [self.device.display_info["width"],
                           self.device.display_info["height"]]
        }
        result = json.loads(proxy.predict(json.dumps(request_json)))
        new_idx = result["indices"]
        text = result["text"]
        new_events = []

        # get rid of infinite recursive by randomizing first event
        if not self.utg.is_state_reached(self.current_state):
            new_first = random.randint(0, len(new_idx) - 1)
            new_idx[0], new_idx[new_first] = new_idx[new_first], new_idx[0]

        for idx in new_idx:
            if isinstance(possible_events[idx], SetTextEvent):
                possible_events[idx].text = text
            new_events.append(possible_events[idx])
        return new_events

    def __get_nav_target(self, current_state):
        # If last event is a navigation event
        if self.__nav_target and self.__event_trace.endswith(EVENT_FLAG_NAVIGATE):
            event_path = self.utg.get_event_path(current_state=current_state, target_state=self.__nav_target)
            if event_path and 0 < len(event_path) <= self.__nav_num_steps:
                # If last navigation was successful, use current nav target
                self.__nav_num_steps = len(event_path)
                return self.__nav_target
            else:
                # If last navigation was failed, add nav target to missing states
                self.__missed_states.add(self.__nav_target.state_str)

        reachable_states = self.utg.get_reachable_states(current_state)
        if self.random_input:
            random.shuffle(reachable_states)

        for state in reachable_states:
            # Only consider foreground states
            if state.get_app_activity_depth(self.app) != 0:
                continue
            # Do not consider missed states
            if state.state_str in self.__missed_states:
                continue
            # Do not consider explored states
            if self.utg.is_state_explored(state):
                continue
            self.__nav_target = state
            event_path = self.utg.get_event_path(current_state=current_state, target_state=self.__nav_target)
            if len(event_path) > 0:
                self.__nav_num_steps = len(event_path)
                return state

        self.__nav_target = None
        self.__nav_num_steps = -1
        return None


class UtgReplayPolicy(InputPolicy):
    """
    Replay DroidBot output generated by UTG policy
    """

    def __init__(self, device, app, replay_output):
        super(UtgReplayPolicy, self).__init__(device, app)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.replay_output = replay_output

        import os
        event_dir = os.path.join(replay_output, "events")
        self.event_paths = sorted([os.path.join(event_dir, x) for x in
                                   next(os.walk(event_dir))[2]
                                   if x.endswith(".json")])
        # skip HOME and start app intent
        self.event_idx = 2
        self.num_replay_tries = 0

    def generate_event(self):
        """
        generate an event based on replay_output
        @return: InputEvent
        """
        while self.event_idx < len(self.event_paths) and \
                self.num_replay_tries < MAX_REPLY_TRIES:
            self.num_replay_tries += 1
            current_state = self.device.get_current_state(self.device.output_dir)
            if current_state is None:
                time.sleep(5)
                self.num_replay_tries = 0
                return KeyEvent(name="BACK")

            curr_event_idx = self.event_idx
            while curr_event_idx < len(self.event_paths):
                event_path = self.event_paths[curr_event_idx]
                with open(event_path, "r") as f:
                    curr_event_idx += 1

                    try:
                        event_dict = json.load(f)
                    except Exception as e:
                        self.logger.info("Loading %s failed" % event_path)
                        continue

                    if event_dict["start_state"] != current_state.state_str:
                        continue

                    self.logger.info("Replaying %s" % event_path)
                    self.event_idx = curr_event_idx
                    self.num_replay_tries = 0
                    return InputEvent.from_dict(event_dict["event"])

            time.sleep(5)

        raise InputInterruptedException("No more record can be replayed.")


class ManualPolicy(UtgBasedInputPolicy):
    """
    manually explore UFG
    """

    def __init__(self, device, app):
        super(ManualPolicy, self).__init__(device, app, False)
        self.logger = logging.getLogger(self.__class__.__name__)

        self.__first_event = True

    def generate_event_based_on_utg(self):
        """
        generate an event based on current UTG
        @return: InputEvent
        """
        if self.__first_event:
            self.__first_event = False
            self.logger.info("Trying to start the app...")
            start_app_intent = self.app.get_start_intent()
            return IntentEvent(intent=start_app_intent)
        else:
            return ManualEvent()
