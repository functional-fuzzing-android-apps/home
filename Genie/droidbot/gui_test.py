import datetime
import glob
import json
import logging
import os
import shutil
from typing import List, Tuple, Dict, Union, Set

import Levenshtein
import pkg_resources
from apted import APTED
from apted.helpers import Tree

from droidbot.device import Device
from droidbot.oracle_checking_logger import OracleCheckingLogger
from droidbot.utils import replace_file, delete_files
from .config_script import ConfigurationScript
from .input_event import EventLog, InputEvent
from .utg import UTG
from .device_state import DeviceState, COLOR_RED_TUPLE

# Different possible results
EXECUTION_RESULT_CRASH = "Crash Error"
EXECUTION_RESULT_NOT_FULLY_REPLAYABLE = "Not Replayable"
EXECUTION_RESULT_SEMANTIC_ERROR = "Semantic Error"
EXECUTION_RESULT_NORMAL = "No Error"
EXECUTION_RESULT_ABNORMAL = "Abnormal"

TEST_TAG_SEED_TEST = "[s]"
TEST_TAG_MUTANT_TEST = "[m]"
TEST_TAG_DYNAMIC_TEST = "[d]"


class ViewDifference(object):
    """
    Represent one view difference between two view trees
    """
    VIEW_CHANGE_OPERATION = "CHANGE"
    VIEW_NEW_OPERATION = "INSERT"
    VIEW_DELETE_OPERATION = "DELETE"

    def __init__(self, from_state_id: int, from_state: DeviceState, to_state_id: int, to_state: DeviceState,
                 from_view: Union[Dict, None], to_view: Union[Dict, None], operation: str,
                 batch_id=0, annotated_utg_json_file_name: str = None):

        self.from_state = from_state
        self.to_state = to_state
        self.from_state_id = from_state_id
        self.to_state_id = to_state_id
        self.from_view = from_view
        self.to_view = to_view
        self.from_view_context_str = None
        self.to_view_context_str = None

        # Type of view diff
        self.operation = operation

        # This id indicates which batch this view diff belongs to during the oracle checking for one mutant
        #   The valid value will start from ONE
        self.oracle_checking_batch_id = batch_id

        self.annotated_utg_json_file_name = annotated_utg_json_file_name

    @staticmethod
    def view_to_dict(view_dict):
        return {
            'temp_id': view_dict['temp_id'],
            'class': view_dict['class'],
            'resource_id': view_dict['resource_id'],
            'text': view_dict['text'],
            'view_str': view_dict['view_str']
        }

    def to_dict(self, test_output_dir):

        if self.operation == ViewDifference.VIEW_CHANGE_OPERATION:
            return {
                "checking_batch_id": self.oracle_checking_batch_id,
                "from_state_str": self.from_state.state_str,
                "to_state_str": self.to_state.state_str,
                "from_state_id": self.from_state_id,
                "to_state_id": self.to_state_id,
                "from_state_json_file": os.path.relpath(self.from_state.json_state_path, test_output_dir),
                "to_state_json_file": os.path.relpath(self.to_state.json_state_path, test_output_dir),
                "annotated_utg_file": self.annotated_utg_json_file_name,
                "operation": "CHANGE",
                "from_view": ViewDifference.view_to_dict(self.from_view),
                "to_view": ViewDifference.view_to_dict(self.to_view)
                # "from_view_context_str": self.from_view_context_str,
                # "to_view_context_str": self.to_view_context_str
            }

        elif self.operation == ViewDifference.VIEW_NEW_OPERATION:
            return {
                "checking_batch_id": self.oracle_checking_batch_id,
                "from_state_str": self.from_state.state_str,
                "to_state_str": self.to_state.state_str,
                "from_state_id": self.from_state_id,
                "to_state_id": self.to_state_id,
                "from_state_json_file": os.path.relpath(self.from_state.json_state_path, test_output_dir),
                "to_state_json_file": os.path.relpath(self.to_state.json_state_path, test_output_dir),
                "annotated_utg_file": self.annotated_utg_json_file_name,
                "operation": "INSERT",
                "from_view": None,
                "to_view": ViewDifference.view_to_dict(self.to_view)
                # "from_view_context_str": self.from_view_context_str,
                # "to_view_context_str": self.to_view_context_str
            }

        else:
            return {
                "checking_batch_id": self.oracle_checking_batch_id,
                "from_state_str": self.from_state.state_str,
                "to_state_str": self.to_state.state_str,
                "from_state_id": self.from_state_id,
                "to_state_id": self.to_state_id,
                "from_state_json_file": os.path.relpath(self.from_state.json_state_path, test_output_dir),
                "to_state_json_file": os.path.relpath(self.to_state.json_state_path, test_output_dir),
                "annotated_utg_file": self.annotated_utg_json_file_name,
                "operation": "DELETE",
                "from_view": ViewDifference.view_to_dict(self.from_view),
                "to_view": None
                # "from_view_context_str": self.from_view_context_str,
                # "to_view_context_str": self.to_view_context_str
            }

    @staticmethod
    def view_from_dict(device_state: DeviceState, view_dict):
        if not isinstance(view_dict, dict):
            return None
        else:
            return device_state.views[view_dict['temp_id']]

    @staticmethod
    def from_dict(view_diff_dict, mutant_test_output_dir, device: Device):
        """
        recover the view diff
        :param view_diff_dict: the view diff
        :param mutant_test_output_dir: the mutant's test output dir
        :param device: the dummy device to recover state
        :return:
        """
        if not isinstance(view_diff_dict, dict):
            return None
        else:
            from_state = device.recover_device_state(
                os.path.abspath(os.path.join(mutant_test_output_dir, view_diff_dict['from_state_json_file'])))

            to_state = device.recover_device_state(
                os.path.abspath(os.path.join(mutant_test_output_dir, view_diff_dict['to_state_json_file'])))

            return ViewDifference(
                view_diff_dict['from_state_id'],
                from_state,
                view_diff_dict['to_state_id'],
                to_state,
                ViewDifference.view_from_dict(from_state, view_diff_dict['from_view']),
                ViewDifference.view_from_dict(to_state, view_diff_dict['to_view']),
                view_diff_dict['operation'],
                view_diff_dict['checking_batch_id'],
                view_diff_dict['annotated_utg_file']
            )

    def __str__(self):
        str_of_view_difference = ""
        if self.operation == ViewDifference.VIEW_CHANGE_OPERATION:
            str_of_view_difference += "CHANGE: " + "(S_" + str(
                self.from_state_id) + "[state_str]" + self.from_state.state_str \
                                      + "[state_json]" + self.from_state.screenshot_path \
                                      + ", S_" + str(self.to_state_id) + "[state_str]" + self.to_state.state_str \
                                      + ")\n\t" + "(" + \
                                      DeviceState.get_view_text_sensitive_signature(self.from_view) + "[view_str]" + \
                                      self.from_view['view_str'] \
                                      + ", \n\t" + \
                                      DeviceState.get_view_text_sensitive_signature(self.to_view) + "[view_str]" + \
                                      self.to_view['view_str'] + ")"

        elif self.operation == ViewDifference.VIEW_NEW_OPERATION:
            str_of_view_difference += "INSERT: " + "(S_" + str(
                self.from_state_id) + "[state_str]" + self.from_state.state_str \
                                      + "[state_json]" + self.from_state.screenshot_path \
                                      + ", S_" + str(self.to_state_id) + "[state_str]" + self.to_state.state_str \
                                      + ")\n\t" + "(-, " + \
                                      DeviceState.get_view_text_sensitive_signature(self.to_view) + "[view_str]" + \
                                      self.to_view['view_str'] + ")"

        else:
            str_of_view_difference += "DELETE: " + "(S_" + str(
                self.from_state_id) + "[state_str]" + self.from_state.state_str \
                                      + "[state_json]" + self.from_state.screenshot_path \
                                      + ", S_" + str(self.to_state_id) + "[state_str]" + self.to_state.state_str \
                                      + ")\n\t" + "(" + \
                                      DeviceState.get_view_text_sensitive_signature(self.from_view) + "[view_str]" + \
                                      self.from_view['view_str'] \
                                      + ", -)"

        return str_of_view_difference

    def get_context_string_of_view_diff(self, include_view_text=True):
        """
        Get the context string of the view diff, which includes two context strings of from_view and to_view, respectively.

        A GUI tree may has multiple views with similar view signatures. In principle, a view's context can uniquely
        locate this view in a GUI tree. To achieve this, a view's context can be encoded via a view trace
        (i.e., a sequence of views) on the GUI tree. This trace starts from an "ancestor" tree node and ends at this
        view. Thus, a view's context can be represented as the view tree rooting at this "ancestor" node. This tree
        can be encoded as a string.

        In practice, we can uniquely identify a view without letting this view trace starting from the tree's root node.
        We can pick a proper "ancestor" node, and convert the corresponding view tree into a string.
        In our implementation, we find the nearest "ancestor" node which has more than one children (the view is one
        of its children).

        (If the ancestor view that has more than one children views, this ancestor will not be included
        in the context tree)

        Some note:

            The context of a leaf view node includes its properties, i.e., class, resource_id, content_desc, text.

            The context of a non-leaf view node includes its properties and the properties of all its children, i.e.,
                a tree rooting by this non-leaf view node.

            Note that a view diff is associated with three possible types of operations:
                NEW, DELETE, CHANGE

        :param include_view_text, whether to include view text
        :return: Tuple(str, str), the brace string of from_view's context tree and to_view's context tree
        """

        if self.from_view is not None:
            ancestor_view = self.from_state.get_ancestor_view_by_tree_level(self.from_view)
            context_string_of_view_diff = self.from_state.get_view_context_string(ancestor_view,
                                                                                  include_view_text=include_view_text)
            self.from_view_context_str = context_string_of_view_diff
        else:
            self.from_view_context_str = "{-}"

        if self.to_view is not None:
            ancestor_view = self.to_state.get_ancestor_view_by_tree_level(self.to_view)
            context_string_of_view_diff = self.to_state.get_view_context_string(ancestor_view,
                                                                                include_view_text=include_view_text)
            self.to_view_context_str = context_string_of_view_diff
        else:
            self.to_view_context_str = "{-}"

        return self.from_view_context_str, self.to_view_context_str


class CheckingResult(object):
    """
    the oracle checking result for one mutant
    """

    def __init__(self, seed_test_id, mutant_test_id, insert_position, is_faithfully_replayed=True,
                 unreplayable_utg_event_ids_prefix=None, is_fully_replayed=True, has_crash_error=False,
                 crash_confidence="", has_semantic_error=False, unmatched_views_of_seed_test=None,
                 unmatched_views_of_mutant_test=None, oracle_checking_batch_cnt=0):

        self.seed_test_id = seed_test_id
        self.mutant_test_id = mutant_test_id
        self.insert_position = insert_position
        self.is_faithfully_replayed = is_faithfully_replayed
        self.is_fully_replayed = is_fully_replayed
        # the prefix of the test which is not replayable given in utg event ids
        self.unreplayable_utg_event_ids_prefix = unreplayable_utg_event_ids_prefix
        self.has_crash_error = has_crash_error
        self.crash_confidence = crash_confidence
        self.has_semantic_error = has_semantic_error

        self.oracle_checking_batch_id_counter = 0
        self.oracle_checking_batch_cnt = oracle_checking_batch_cnt

        # unmatched views from the seed test w.r.t the mutant test
        self.unmatched_views_of_seed_test: List[
            ViewDifference] = [] if unmatched_views_of_seed_test is None else unmatched_views_of_seed_test

        # unmatched views from the mutant test w.r.t the seed test
        self.unmatched_views_of_mutant_test: List[
            ViewDifference] = [] if unmatched_views_of_mutant_test is None else unmatched_views_of_mutant_test

    def set_crash_checking_result(self, has_crash: bool, crash_confidence: str):
        self.has_crash_error = has_crash
        self.crash_confidence = crash_confidence

    def set_semantic_checking_result(self, has_semantic_error: bool):
        self.has_semantic_error = has_semantic_error

    def set_replay_info(self, is_faithfully_replayed: bool, is_fully_replayed: bool, unreplayable_utg_event_ids_prefix):
        self.is_faithfully_replayed = is_faithfully_replayed
        self.is_fully_replayed = is_fully_replayed
        self.unreplayable_utg_event_ids_prefix = unreplayable_utg_event_ids_prefix

    def add_unmatched_views(self, unmatched_views_of_seed_test: List[ViewDifference],
                            unmatched_views_of_mutant_test: List[ViewDifference]):

        self.oracle_checking_batch_id_counter += 1
        for unmatched_view in unmatched_views_of_seed_test:
            unmatched_view.oracle_checking_batch_id = self.oracle_checking_batch_id_counter
        self.unmatched_views_of_seed_test.extend(unmatched_views_of_seed_test)

        if len(unmatched_views_of_mutant_test) != 0:
            # add if we do have unmatched views in this list
            for unmatched_view in unmatched_views_of_mutant_test:
                unmatched_view.oracle_checking_batch_id = self.oracle_checking_batch_id_counter
            self.unmatched_views_of_mutant_test.extend(unmatched_views_of_mutant_test)

    @staticmethod
    def filter_view_diffs(unmatched_views, ignored_views: dict, ignore_pages: dict, ignored_view_children_order: dict):
        """
        filter irrelevant view diffs according to oracle checking configurations, also ignore these views in the
            corresponding states.
        :param unmatched_views:
        :param ignored_views:
        :param ignore_pages:
        :param ignored_view_children_order
        :return:
        """
        filtered_unmatched_views: List[ViewDifference] = []

        for view_diff in unmatched_views:

            # If the view_diff's from_state or to_state belongs to specific page types, then we ignore the view diff.
            #   For now, we ignore '.TimePickerActivity', '.DatePickerActivity'
            ignored_pages = False
            foreground_activities_of_view_diff = [view_diff.from_state.foreground_activity, view_diff.to_state.foreground_activity]
            for activity_name in foreground_activities_of_view_diff:
                if '.TimePickerActivity' in activity_name or '.DatePickerActivity' in activity_name or '.DateAndTimePickerActivity' in activity_name:
                    ignored_pages = True
                    break
            if ignored_pages:
                continue

            # If the view_diff's from_view or to_view belongs to specific views, then we ignore the corresponding view
            for view_key in ignored_views:
                ignored_view_dict = ignored_views[view_key]

                if view_diff.from_state is not None and view_diff.from_view is not None:
                    cond1 = (ignored_view_dict['activity'] == view_diff.from_state.foreground_activity)
                    cond2 = DeviceState.are_views_match(ignored_view_dict, view_diff.from_view)
                    if cond1 and cond2:
                        print("-- Matched ignored views, Filtered-- ")
                        view_diff.from_view = None

                if view_diff.to_state is not None and view_diff.to_view is not None:
                    cond1 = (ignored_view_dict['activity'] == view_diff.to_state.foreground_activity)
                    cond2 = DeviceState.are_views_match(ignored_view_dict, view_diff.to_view)
                    if cond1 and cond2:
                        print("-- Matched ignored views, Filtered-- ")
                        view_diff.to_view = None

            if view_diff.from_view is not None or view_diff.to_view is not None:
                view_diff.from_state.ignore_views_in_device_state(ignored_views)
                view_diff.from_state.ignore_views_order_in_device_state(ignored_view_children_order)
                view_diff.to_state.ignore_views_in_device_state(ignored_views)
                view_diff.to_state.ignore_views_order_in_device_state(ignored_view_children_order)
                filtered_unmatched_views.append(view_diff)

        return filtered_unmatched_views

    def compute_unique_errors(self, ignore_views, ignore_pages, ignored_view_children_order, gui_page_types_info,
                              include_view_text=True):

        """
        compute unique errors within a single mutant
        :return:
        """

        # computing unique errors
        dict_of_unique_semantic_error_instances: Dict[str, Tuple[str, str]] = dict()
        list_of_pruned_semantic_error_instances: List[str] = []

        # Remove ignored views before computing errors
        # Note: this step should be done after finishing the recovery the checking results (otherwise it will disturb
        #   the recovery of view diffs), and before computing the errors.
        filtered_unmatched_views_of_seed_test = \
            CheckingResult.filter_view_diffs(self.unmatched_views_of_seed_test, ignore_views, ignore_pages,
                                             ignored_view_children_order)
        filtered_unmatched_views_of_mutant_test = \
            CheckingResult.filter_view_diffs(self.unmatched_views_of_mutant_test, ignore_views, ignore_pages,
                                             ignored_view_children_order)

        for i in range(1, self.oracle_checking_batch_cnt + 1):

            filtered_unmatched_views_of_seed_test_at_batch_i = [view_diff for view_diff in
                                                                filtered_unmatched_views_of_seed_test
                                                                if view_diff.oracle_checking_batch_id == i]

            filtered_unmatched_views_of_mutant_test_at_batch_i = [view_diff for view_diff in
                                                                  filtered_unmatched_views_of_mutant_test
                                                                  if view_diff.oracle_checking_batch_id == i]

            # Note: we do oracle checking again to see whether this reported error is a real false positive,
            #   and use the new unmatched views between seed test and mutant test to merge reported errors
            is_contained, filtered_unmatched_views_of_seed_test_at_batch_i, filtered_unmatched_views_of_mutant_test_at_batch_i = \
                GUITestCase.check_view_diffs_containment(filtered_unmatched_views_of_seed_test_at_batch_i,
                                                         filtered_unmatched_views_of_mutant_test_at_batch_i)
            if is_contained:
                continue

            # Check whether the view diffs are from two comparable GUI pages according to annotation info.
            # Note: we only check seed test
            first_view_diff_of_seed_test = filtered_unmatched_views_of_seed_test_at_batch_i[0]
            gui_page_type_of_from_state = first_view_diff_of_seed_test.from_state.get_gui_page_type(gui_page_types_info)
            gui_page_type_of_to_state = first_view_diff_of_seed_test.to_state.get_gui_page_type(gui_page_types_info)
            if gui_page_type_of_from_state != gui_page_type_of_to_state:
                continue

            tmp_list_of_seed_test = []
            for view_diff in filtered_unmatched_views_of_seed_test_at_batch_i:
                from_view_context_str, to_view_context_str = view_diff.get_context_string_of_view_diff(
                    include_view_text=include_view_text)
                # print("[s] checking_batch_id: %d, from_state_id: %d, to_state_id: %d" % (
                #     i, view_diff.from_state_id, view_diff.to_state_id))
                # print("from_view_context_str: %s" % from_view_context_str)
                # print("to_view_context_str: %s" % to_view_context_str)
                tmp_list_of_seed_test.append(from_view_context_str + "/" + to_view_context_str)

            error_str_of_seed_test_at_batch_i = ",".join(sorted(tmp_list_of_seed_test))

            ####

            tmp_list_of_mutant_test = []
            for view_diff in filtered_unmatched_views_of_mutant_test_at_batch_i:
                from_view_context_str, to_view_context_str = view_diff.get_context_string_of_view_diff(
                    include_view_text=include_view_text)
                # print("[m] checking_batch_id: %d, from_state_id: %d, to_state_id: %d" % (
                #     i, view_diff.from_state_id, view_diff.to_state_id))
                # print("from_view_context_str: %s" % from_view_context_str)
                # print("to_view_context_str: %s" % to_view_context_str)
                tmp_list_of_mutant_test.append(from_view_context_str + "/" + to_view_context_str)

            error_str_of_mutant_test_at_batch_i = ",".join(sorted(tmp_list_of_mutant_test))

            error_str_tuple_at_batch_i = (error_str_of_seed_test_at_batch_i, error_str_of_mutant_test_at_batch_i)

            unique_error_id = "/".join(
                [self.seed_test_id, self.mutant_test_id, "insert_position_" + str(self.insert_position),
                 "index_aligned_" + str(i) + ".html"])

            # search for similar errors
            ids_of_similar_errors = [error_id for error_id in dict_of_unique_semantic_error_instances if
                                     error_str_tuple_at_batch_i == dict_of_unique_semantic_error_instances[
                                         error_id]]

            if len(ids_of_similar_errors) <= 0:
                # no similar errors exist -> this is a new error
                dict_of_unique_semantic_error_instances[unique_error_id] = error_str_tuple_at_batch_i

            else:
                # similar errors exist -> this is a duplicate error
                list_of_pruned_semantic_error_instances.append(unique_error_id)
                print("\t duplicated: %s --> %s" % (unique_error_id, ids_of_similar_errors[0]))
                pass

        return dict_of_unique_semantic_error_instances, list_of_pruned_semantic_error_instances

    @staticmethod
    def from_dict(checking_result_dict, mutant_test_output_dir, device: Device):
        if not isinstance(checking_result_dict, dict):
            return None
        else:
            # recover unmatched_views_of_seed_test
            tmp_unmatched_views = checking_result_dict['unmatched_views_of_seed_test']
            unmatched_views_of_seed_test: List[ViewDifference] = []
            for view_diff_dict in tmp_unmatched_views:
                view_diff = ViewDifference.from_dict(view_diff_dict, mutant_test_output_dir, device)
                unmatched_views_of_seed_test.append(view_diff)

            # recover unmatched_views_of_mutant_test
            tmp_unmatched_views = checking_result_dict['unmatched_views_of_mutant_test']
            unmatched_views_of_mutant_test: List[ViewDifference] = []
            for view_diff_dict in tmp_unmatched_views:
                view_diff = ViewDifference.from_dict(view_diff_dict, mutant_test_output_dir, device)
                unmatched_views_of_mutant_test.append(view_diff)

            return CheckingResult(checking_result_dict['seed_test_id'],
                                  checking_result_dict['mutant_test_id'],
                                  checking_result_dict['insert_position'],
                                  is_faithfully_replayed=checking_result_dict['is_faithfully_replayed'],
                                  unreplayable_utg_event_ids_prefix=checking_result_dict[
                                      'unreplayable_utg_event_ids_prefix'],
                                  is_fully_replayed=checking_result_dict['is_fully_replayed'],
                                  has_crash_error=checking_result_dict['crash_error'],
                                  has_semantic_error=checking_result_dict['semantic_error'],
                                  oracle_checking_batch_cnt=checking_result_dict['oracle_checking_batch_cnt'],
                                  unmatched_views_of_seed_test=unmatched_views_of_seed_test,
                                  unmatched_views_of_mutant_test=unmatched_views_of_mutant_test
                                  )

    @staticmethod
    def unmatched_views_to_dict(unmatched_views, test_output_dir):
        """
        convert unmatched views to dict
        :return:
        """
        ret = []

        for view_diff in unmatched_views:
            ret.append(view_diff.to_dict(test_output_dir))

        return ret

    def to_dict(self, test_output_dir: str):
        return {
            "seed_test_id": self.seed_test_id,
            "mutant_test_id": self.mutant_test_id,
            "crash_error": self.has_crash_error,
            "semantic_error": self.has_semantic_error,
            "insert_position": self.insert_position,
            "is_faithfully_replayed": self.is_faithfully_replayed,
            "is_fully_replayed": self.is_fully_replayed,
            "oracle_checking_batch_cnt": self.oracle_checking_batch_id_counter,
            "unreplayable_utg_event_ids_prefix": self.unreplayable_utg_event_ids_prefix,
            "number_of_unmatched_views": len(self.unmatched_views_of_seed_test),
            "unmatched_views_of_seed_test": CheckingResult.unmatched_views_to_dict(self.unmatched_views_of_seed_test,
                                                                                   test_output_dir),
            "unmatched_views_of_mutant_test": CheckingResult.unmatched_views_to_dict(
                self.unmatched_views_of_mutant_test, test_output_dir),
        }


class GUITestCase(object):
    """
    A GUI test case, which represents a sequence of event logs.
    Each event log is composed of event, its from_state and its to_state.

    In the current implementation, the seed tests (including states, event logs, views) are stored in the main output dir,
        while the mutant tests (including states, event logs, views) are stored in their own mutant dirs.
        The main consideration is: (1) We will execute the mutant tests in parallel, and this design can avoid file write
        conflict when executing mutant tests. (2) All seed tests are generated by one thread, and we do not need to worry.
        The original utg is stored in the main output dir.

    """

    def __init__(self, device, app, random_input, test_output_dir=None, test_id=None, test_tag=None,
                 insert_start_position=-1, insert_end_position=-1, independent_trace_len=0,
                 utg_event_ids_of_test=None):

        self.logger = logging.getLogger(self.__class__.__name__)
        self.device = device
        self.app = app
        self.random_input = random_input

        # id of the test, e.g., seed-test-x, mutant-x-y (x - insertion position, y - id)
        self.test_id: str = test_id

        # tag of the test, which indicates different test types,
        #   including [seed-test], [mutant-test], and [dynamic-test]
        self.test_tag = test_tag

        # actual event logs for execution
        self.event_logs: List[EventLog] = []

        # the sequence of utg event ids (on the clustered utg) of the test case (the default value is [])
        # this sequence is used for filtering infeasible test cases
        self.utg_event_ids_of_test = utg_event_ids_of_test if utg_event_ids_of_test is not None else []

        # dir for outputting test execution info
        self.test_output_dir = test_output_dir
        # if os.path.exists(self.output_dir) and self.test_tag == TEST_TAG_MUTANT_TEST:
        #     # delete the mutant test dir before each creation
        #     shutil.rmtree(self.output_dir)
        if not os.path.exists(self.test_output_dir):
            os.makedirs(self.test_output_dir)
            from .utils import init_visualization_env
            init_visualization_env(self.test_output_dir)

        # logcat file for recording monitoring background running info.
        self.logcat_file = os.path.join(self.test_output_dir, "logcat.txt")

        # does this test crash?
        self.has_crash = False
        self.crash_confidence = ""

        # utg that is used to visualize the test
        self.utg = UTG(device=self.device, app=self.app, random_input=self.random_input)

        # position (start from 0, w.r.t the seed test) which the new event logs were inserted at
        #   corresponding to the index in seed_test.event_logs
        # Note only the mutant test has valid values, the seed test has the default invalid value (-1)
        self.insert_start_position = insert_start_position

        # position (start from 0, w.r.t the mutant test) that the new event logs ended at
        #   corresponding to the index in mutant_test.event_logs
        # Note only the mutant test has valid values, the seed test has the default invalid value (-1)
        self.insert_end_position = insert_end_position

        # position (of the STATIC mutant test, start from 0) that the actual execution ended at
        #   corresponding to the index of self.event_logs
        # Note only the mutant test has valid values, the seed test has the default invalid value (-1)
        self.unreplayable_event_log_index = -1

        # length of inserted independent event trace
        # Note only the mutant test has valid values, the seed test has the default invalid value (-1)
        self.independent_trace_len = independent_trace_len

        # Is the mutant test faithfully replayed (for DYNAMIC mutant test)?
        #   If any event is not precisely matched during the mutant execution, then we will set this flag as False.
        #   In this case, if any semantic errors were reported from this mutant, its priority will be set as LOW.
        self.is_faithfully_replayed: bool = True

        self.is_fully_replayed: bool = True

        self.unreplayable_utg_event_ids_prefix = []

        self.has_semantic_error: bool = False

        # confidence of giving the execution result
        self.confidence_of_result = None

        # unique id for recording semantic errors
        self.gui_semantic_error_id = 0

        # unique id for generating new screenshot path
        self.unique_id = 0

        # checking result of the mutant test
        self.checking_result = None

    def clean_mutant_data(self, clean_oracle_data=False, clean_runtime_data=False):
        if os.path.exists(self.test_output_dir) and clean_oracle_data:
            html_files = glob.glob(os.path.join(self.test_output_dir, "index_*.html"))
            delete_files(html_files)
            utg_files = glob.glob(os.path.join(self.test_output_dir, "utg_*.js*"))
            delete_files(utg_files)
            # log_files = glob.glob(os.path.join(self.test_output_dir, "*.log"))
            # delete_files(log_files)
        if os.path.exists(self.test_output_dir) and clean_runtime_data:
            coverage_file = glob.glob(os.path.join(self.test_output_dir, "coverage.ec"))
            delete_files(coverage_file)
            logcat_file = glob.glob(os.path.join(self.test_output_dir, "logcat.txt"))
            delete_files(logcat_file)

    def add_event_log(self, event_log):
        """
        add one event log
        :param event_log:
        :return:
        """
        if event_log is None:
            return
        self.event_logs.append(event_log)

    def add_event_logs(self, event_logs):
        """
        add a list of event logs
        :param event_logs:
        :return:
        """
        if event_logs is None:
            return

        self.event_logs.extend(event_logs)

    def add_utg_event_id(self, utg_event_id):
        """
        add one utg event id
        :param utg_event_id:
        :return:
        """
        self.utg_event_ids_of_test.append(utg_event_id)

    def add_utg_event_ids(self, utg_event_ids):
        """
        add a sequence of utg event ids
        :param utg_event_ids:
        :return:
        """
        self.utg_event_ids_of_test.extend(utg_event_ids)

    def convert_utg_event_ids_to_trie_prefix(self, event_id_index=None):
        """
        convert the utg event ids to the trie prefix (from 0 until event_id_index, i.e., [0, event_id_index])
        :param event_id_index:
        :return:
        """
        if event_id_index is None:
            # get the whole trace if event_id_index is None
            end_index = len(self.utg_event_ids_of_test)
        else:
            end_index = event_id_index + 1

        target_utg_event_ids = self.utg_event_ids_of_test[0: end_index]
        trie_prefix = ""
        for i in target_utg_event_ids:
            trie_prefix += "/" + str(i)
        return trie_prefix

    def get_insert_start_position(self):
        return self.insert_start_position

    def set_insert_position(self, insert_position: int, independent_trace_len: int):
        """
        The insert event log's index locates in [self.insert_start_position, self.insert_end_position)

        :param insert_position:
        :param independent_trace_len:
        :return:
        """
        self.insert_start_position = insert_position
        self.independent_trace_len = independent_trace_len
        self.insert_end_position = insert_position + independent_trace_len

    def check_test_case_validity(self):

        test_utg_json_file_path = os.path.join(self.test_output_dir, "utg.json")
        assert (
            os.path.exists(test_utg_json_file_path)
        ), "Cannot find %s, please check whether you have already constructed the utg?" % test_utg_json_file_path

        return test_utg_json_file_path

    @staticmethod
    def load_test_case_runtime_data(checking_result_file_path):

        checking_result_file = open(checking_result_file_path, "r")
        checking_result_dict = json.load(checking_result_file)
        return (checking_result_dict['crash_error'], checking_result_dict['is_faithfully_replayed'],
                checking_result_dict['is_fully_replayed'], checking_result_dict['unreplayable_utg_event_ids_prefix'])

    def load_test_case_utg(self, utg_json_file_path):

        # Start the recovery
        utg_json_file = open(utg_json_file_path, "r")
        utg_json_data = json.load(utg_json_file)
        # close the utg json file
        utg_json_file.close()

        # get the values of 'insert_start_position' and 'independent_trace_len'
        insert_start_position = None
        independent_trace_len = None
        utg_event_ids_of_test = None
        if 'insert_start_position' in utg_json_data:
            insert_start_position = utg_json_data['insert_start_position']
        if 'independent_trace_len' in utg_json_data:
            independent_trace_len = utg_json_data['independent_trace_len']
        if 'utg_event_ids_of_test' in utg_json_data:
            utg_event_ids_of_test = utg_json_data['utg_event_ids_of_test']

        if self.test_tag == TEST_TAG_MUTANT_TEST or self.test_tag == TEST_TAG_DYNAMIC_TEST:
            # We only check these fields for the mutant test
            assert (
                    insert_start_position != -1 and
                    independent_trace_len != 0 and
                    utg_event_ids_of_test != []
            ), 'insert_start_position, independent_trace_len, or utg_event_ids_of_test is not correct when recovering!'

        utg_nodes = utg_json_data['nodes']  # get the utg nodes
        utg_edges = utg_json_data['edges']  # get the utg edges

        # the set of utg states in the form of the dict {state_str: DeviceState}
        utg_states = {}
        for node in utg_nodes:
            # recover the device state
            state_json_file = os.path.join(self.test_output_dir, node['state_json_file_path'])
            state = self.device.recover_device_state(state_json_file,
                                                     screenshot_path=os.path.join(self.test_output_dir, node['image']),
                                                     first_state=("<FIRST>" in node['label']),
                                                     last_state=("<LAST>" in node['label']))
            node_state_str = node['state_str']
            utg_states[node_state_str] = state

        # the set of utg transitions in the form of dict {edge_id: Edge}
        #   Here, edge['id'] is in the form of "from_state.state_str-->to_state.state_str"
        utg_transitions = {}
        for edge in utg_edges:
            edge_id = edge['id']
            if self.test_tag == TEST_TAG_MUTANT_TEST:
                # If recovering a mutant test, do not recover the events of seed test or dynamic test if exist.
                # We only care the events of mutant test
                if TEST_TAG_DYNAMIC_TEST in edge_id or \
                        TEST_TAG_SEED_TEST in edge_id:
                    continue
            if self.test_tag == TEST_TAG_DYNAMIC_TEST:
                # If recovering a dynamic test, do not recover the events of seed test or mutant test if exist.
                # We only care the events of dynamic test
                if TEST_TAG_MUTANT_TEST in edge_id or \
                        TEST_TAG_SEED_TEST in edge_id:
                    continue
            utg_transitions[edge_id] = edge

        return utg_states, utg_transitions, insert_start_position, independent_trace_len, utg_event_ids_of_test

    def recover_test_case(self, overwrite=False):
        """
        recover the test case (including the seed test and the mutant test) from the file system
        :overwrite: whether to overwrite when recovering the test case
            # DO NOT overwrite the *seed test*'s utg, since it will be loaded by multiple fuzzing threads.
            # Do overwrite the *mutant test*'s utg if we will execute the mutant test,
                since we only need to keep the events of mutant test
        :return: GUITestCase
        """

        # Check test case validity
        test_utg_json_file_path = self.check_test_case_validity()

        # Load the test case's utg
        utg_states, utg_transitions, insert_start_position, independent_trace_len, utg_event_ids_of_test = \
            self.load_test_case_utg(test_utg_json_file_path)

        # the basename of test dir is the test id
        self.test_id = os.path.basename(os.path.abspath(self.test_output_dir))
        # create the GUI test case
        self.insert_start_position = insert_start_position
        self.insert_end_position = insert_start_position + independent_trace_len
        self.independent_trace_len = independent_trace_len
        self.utg_event_ids_of_test = utg_event_ids_of_test

        if self.test_tag == TEST_TAG_DYNAMIC_TEST:
            checking_result_file = os.path.join(self.test_output_dir, "checking_result.json")
            if os.path.exists(checking_result_file):
                has_crash, is_faithfully_replayed, is_fully_replayed, unreplayable_utg_event_ids_prefix = \
                    GUITestCase.load_test_case_runtime_data(checking_result_file)
                self.has_crash = has_crash
                self.is_faithfully_replayed = is_faithfully_replayed
                self.is_fully_replayed = is_fully_replayed
                self.unreplayable_utg_event_ids_prefix = unreplayable_utg_event_ids_prefix

        # data structure:
        #   str: the utg transition (event) id
        #   EventLog: the event log
        event_logs_of_test_case: List[Tuple[str, EventLog]] = []

        # iterate over utg transitions to recover the utg and collect event logs
        for utg_transition_dict in utg_transitions.values():
            utg_transition_events = utg_transition_dict['events']
            for utg_transition_event_dict in utg_transition_events:

                # get the from_state and to_state
                from_state = utg_states[utg_transition_dict['from']]
                to_state = utg_states[utg_transition_dict['to']]

                # load the event log file
                event_log_file_path = \
                    os.path.abspath(
                        os.path.join(self.test_output_dir, utg_transition_event_dict['event_log_file_path']))

                assert (
                    os.path.exists(event_log_file_path)
                ), "[Recover Test Case] event_log_file_path does not exists!"

                event_views_file_path = [os.path.abspath(os.path.join(self.test_output_dir, event_view_file_path))
                                         for event_view_file_path in
                                         utg_transition_event_dict['view_images']]

                with open(event_log_file_path, "r") as f:
                    try:
                        # event_log_dict is in the form of EventLog
                        event_log_dict = json.load(f)
                    except Exception as e:
                        self.logger.info("Loading %s failed when recovering the original utg: %s" %
                                         (event_log_file_path, e))
                    event = InputEvent.from_dict(event_log_dict['event'])
                assert (
                        event is not None
                ), "Load event from event log file failed when recovering the original utg!"

                event_tag = event_log_dict['tag']
                event_str = utg_transition_event_dict['event_str']
                event_utg_id = utg_transition_event_dict['event_id']

                event_color = utg_transition_event_dict['event_color']
                is_inserted_event = utg_transition_event_dict['is_inserted_event']

                # recover the utg of mutant test
                self.utg.add_utg_transition_for_gui_test(event,
                                                         from_state,
                                                         to_state,
                                                         event_id=event_utg_id,
                                                         event_str=event_str,
                                                         event_log_file_path=event_log_file_path,
                                                         event_views_file_path=event_views_file_path,
                                                         utg_output_dir=self.test_output_dir,
                                                         gui_test_tag=self.test_tag,
                                                         event_color=event_color,
                                                         is_inserted_event=is_inserted_event,
                                                         insert_start_position=insert_start_position,
                                                         independent_trace_len=independent_trace_len,
                                                         utg_event_ids_of_test=utg_event_ids_of_test,
                                                         output_utg=overwrite)

                event_log = EventLog(self.device, self.app,
                                     event,
                                     profiling_method=None,
                                     tag=event_tag,
                                     event_str=event_str,
                                     utg_event_id=event_utg_id,
                                     is_inserted_event=is_inserted_event,
                                     event_views_file_path=event_views_file_path,
                                     event_log_json_file_path=event_log_file_path,
                                     from_state=from_state,
                                     to_state=to_state)

                # recover the event logs of mutant test
                # Fixed issue #23
                event_logs_of_test_case.append((event_utg_id, event_log))

        for event_log_tuple in sorted(event_logs_of_test_case, key=lambda x: x[0]):
            self.add_event_log(event_log_tuple[1])

        return self

    def get_utg_event_ids_on_clustered_utg(self, clustered_utg: UTG):
        """
        Map a test (seed or mutant) to the clustered utg
        Return a sequence of utg event ids on the clustered utg
        :return: (List[int], List[str])
        """

        # get the event logs
        event_logs_of_test: List[EventLog] = self.event_logs

        # the utg event ids that are mapped by the seed test
        utg_event_ids_of_test: List[int] = []

        # the transition info
        transition_annotation_info: List[str] = []

        event_logs_len: int = len(event_logs_of_test)
        for i in range(event_logs_len):

            event_log = event_logs_of_test[i]

            # map the event log to the clustered utg
            event_log.map_to_cluster_utg()

            # find the source state on the cluster utg
            from_state_structure_str: str = event_log.from_state_structure_str
            to_state_structure_str: str = event_log.to_state_structure_str
            event = event_log.event

            assert (
                    (from_state_structure_str in clustered_utg.G.nodes) and
                    (to_state_structure_str in clustered_utg.G.nodes)
            ), "Cannot map test's states to the clustered utg's state!"

            # the cluster utg event id that is mapped by the event of event_log
            clustered_utg_event_id = None

            for tmp_event_str in clustered_utg.G[from_state_structure_str][to_state_structure_str]["events"]:
                tmp_event_dict = clustered_utg.G[from_state_structure_str][to_state_structure_str]["events"][
                    tmp_event_str]
                tmp_event = tmp_event_dict['event']
                tmp_event_id = tmp_event_dict['id']

                if DeviceState.equal_input_events(tmp_event, event):
                    clustered_utg_event_id = tmp_event_id
                    break

            assert (
                    clustered_utg_event_id is not None
            ), "Cannot map test's event to the clustered utg's event!"

            utg_event_ids_of_test.append(clustered_utg_event_id)

            if event_log.is_inserted_event:
                transition_annotation_info.append(str(clustered_utg_event_id) + "@" + str(i) + "-m")
            else:
                transition_annotation_info.append(str(clustered_utg_event_id) + "@" + str(i) + "-s")

        return utg_event_ids_of_test, transition_annotation_info

    def merge_with_another_test(self, another_test: 'GUITestCase', output_utg=True):
        """
        Merge the current test's utg with another test's utg
        :param another_test: the test whose utg will be merged into the current test's utg
        :param output_utg:
        :return:
        """
        if another_test is None:
            return

        another_test_utg = another_test.utg

        for state_transition in another_test_utg.G.edges():
            # get the state_str
            from_state_str: str = state_transition[0]
            to_state_str: str = state_transition[1]
            # get the state
            from_state = another_test_utg.G.nodes[from_state_str]["state"]
            to_state = another_test_utg.G.nodes[to_state_str]["state"]
            # get the events between from_state and to_state
            events = another_test_utg.G[from_state_str][to_state_str]["events"]

            event_list = []
            for event_str, event_info in sorted(iter(events.items()), key=lambda x: x[1]["id"]):
                event_list.append({
                    "event_str": event_str,
                    "event_id": event_info["id"],
                    "event": event_info["event"],
                    "color": event_info["color"],
                    "is_inserted_event": event_info["is_inserted_event"],
                    "event_log_file_path": event_info["event_log_file_path"],
                    "event_views_file_path": event_info["event_views_file_path"]
                })

            for event_dict in event_list:
                # Deepcopy the states from the seed test
                # We do not want to disturb the seed test's states.
                from_state_copy = DeviceState.deepcopy_device_state(from_state, self.device)
                to_state_copy = DeviceState.deepcopy_device_state(to_state, self.device)
                self.utg.add_utg_transition_for_gui_test(event_dict["event"],
                                                         from_state_copy,
                                                         to_state_copy,
                                                         event_id=event_dict["event_id"],
                                                         event_str=event_dict["event_str"],
                                                         event_log_file_path=event_dict['event_log_file_path'],
                                                         # specific path of the seed test's view files
                                                         event_views_file_path=event_dict['event_views_file_path'],
                                                         utg_output_dir=self.test_output_dir,
                                                         gui_test_tag=another_test.test_tag,
                                                         event_color=event_dict['color'],
                                                         is_inserted_event=event_dict['is_inserted_event'],
                                                         insert_start_position=self.insert_start_position,
                                                         independent_trace_len=self.independent_trace_len,
                                                         utg_event_ids_of_test=self.utg_event_ids_of_test,
                                                         output_utg=output_utg)

    def construct_test_utg_based_on_event_logs(self):
        """
        construct the utg of the test via its event logs
        :return:
        """
        if len(self.event_logs) == 0:
            # do nothing if no event logs exist
            return

        for event_log in self.event_logs:
            event = event_log.event
            from_state = event_log.from_state
            to_state = event_log.to_state
            event_color = event_log.color_tag  # newly inserted event sequences are annotated as red
            event_views_file_path = event_log.event_views_file_path

            self.utg.add_utg_transition_for_gui_test(event, from_state, to_state,
                                                     event_log_file_path=event_log.event_log_json_file_path,
                                                     event_views_file_path=event_views_file_path,
                                                     utg_output_dir=self.test_output_dir,
                                                     gui_test_tag=self.test_tag,
                                                     event_color=event_color,
                                                     is_inserted_event=event_log.is_inserted_event,
                                                     insert_start_position=self.insert_start_position,
                                                     independent_trace_len=self.independent_trace_len,
                                                     utg_event_ids_of_test=self.utg_event_ids_of_test)

    def get_input_event_from_test_by_index(self, index):
        """
        Get the input event from the test by its index in the event log
        :param index: the index (starts from ZERO)
        :return:
        """
        event_log = self.event_logs[index]
        return event_log.event

    def get_from_state_from_test_by_index(self, index):
        """
        Get an input event's from_state by its index in the event log
        :param index: the index (starts from ZERO)
        :return: DeviceState
        """
        if not (0 <= index < len(self.event_logs)):
            return None
        event_log = self.event_logs[index]
        return event_log.from_state

    def compute_comparable_states(self, aligned_states_of_gui_test, gui_page_types_info=None):
        """
        Compute the comparable states from the given test.

        The output is a list of comparable device states:
            (index_of_from_state_in_states_comparison_array, from_state, index_of_from_state_in_test_utg,
            index_of_to_state_in_states_comparison_array, to_state, index_of_to_state_in_test_utg)

        :param aligned_states_of_gui_test: list of aligned states of a test for comparison
        :param gui_page_types_info: the configuration script
        :return: List[Tuple[int, DeviceState, int, int, DeviceState, int]]
        """

        # check the validity of comparable_event_logs_len
        valid_states_cnt = 0
        insert_position = -1
        for i in range(0, len(aligned_states_of_gui_test)):
            state = aligned_states_of_gui_test[i]
            if state is not None:
                valid_states_cnt += 1
            else:
                valid_states_cnt += 1
                insert_position = i

        if valid_states_cnt <= 1 or insert_position == -1:
            # give up state comparison if no enough states exists or no insertion position exists
            return []

        #  Data structure:
        #  Tuple(index_of_from_state_in_states_comparison_array, from_state,
        #          index_of_from_state_in_test_utg,
        #        index_of_to_state_in_states_comparison_array, to_state,
        #          index_of_to_state_in_test_utg)
        #  Example:
        #   index_of_from_state_in_states_comparison_array: the index of from_state in the valid_states_for_comparison,
        #       which is used to compute gui page differences
        #   index_of_from_state_in_test_utg: the index of from_state in the test utg, which is used to draw
        #       view differences on the corresponding gui pages in the test utg.
        #
        #   The difference is that: state_id starts from ZERO; utg_state_id starts from ONE!
        comparable_states: List[Tuple[int, DeviceState, int, int, DeviceState, int]] = []

        range_i = list(range(0, valid_states_cnt))
        min_j = insert_position + 1
        max_j = valid_states_cnt

        # Pair any comparable states, i is the index of event_logs
        for i in range_i:

            if aligned_states_of_gui_test[i] is None:
                # skip the insertion position flag before fetching the state
                continue

            from_state = aligned_states_of_gui_test[i][0]

            if not from_state.foreground_activity.startswith(self.app.get_package_name()):
                # skip this state if it is from the app under test to reduce false positives
                continue

            from_state_id_in_test_utg = aligned_states_of_gui_test[i][1]
            from_state_index_of_aligned_states_list = i

            j = max(i + 1, min_j)
            while min_j <= j < max_j:

                if aligned_states_of_gui_test[j] is None:
                    # skip the insertion position flag before fetching the state
                    j += 1
                    continue

                to_state = aligned_states_of_gui_test[j][0]

                if not to_state.foreground_activity.startswith(self.app.get_package_name()):
                    # skip this state if it is from the app under test to reduce false positives
                    j += 1
                    continue

                to_state_id_in_test_utg = aligned_states_of_gui_test[j][1]
                to_state_index_of_aligned_states_list = j

                are_comparable = DeviceState.are_comparable_states(from_state, to_state, gui_page_types_info)
                if are_comparable:
                    # Record the state pair (current_state, next_state) only if next_state is behind the insert
                    #   position, meanwhile current_state and next_state is comparable
                    self.logger.info("Utg State %d (%s, %d) and %d (%s, %d) are comparable" % (
                        from_state_id_in_test_utg, from_state.state_str,
                        from_state_index_of_aligned_states_list,
                        to_state_id_in_test_utg, to_state.state_str,
                        to_state_index_of_aligned_states_list))

                    comparable_states.append((from_state_index_of_aligned_states_list,
                                              from_state,
                                              from_state_id_in_test_utg,
                                              to_state_index_of_aligned_states_list,
                                              to_state,
                                              to_state_id_in_test_utg))

                j += 1

        return comparable_states

    def compare_mutant_and_seed_test(self, comparable_states_of_mutant_test,
                                     comparable_states_of_seed_test,
                                     aligned_states_of_mutant_test,
                                     aligned_states_of_seed_test,
                                     config_script: ConfigurationScript):

        """
        Leverage the tree edit distance to identify the GUI differences between two comparable GUI pages
        Note:
            1. These two GUI pages belong to the SAME test, and they are COMPARABLE.
            2. The edit distance is computed based on two WHOLE TREEs of these two GUI pages.
            3. We use the "[class].[resource-id].[text]." to represent each tree node.

        TODO: we may need an XPTH rules to help filter volatile view elements, this can be app-specific,
            and greatly reduce false positives.

        The current implementation: we ignore these volatile view elements when computing gui differences

        Related info:
        1. the algorithm we use here: https://github.com/JoaoFelipe/apted
        2. the classic zhang-shasha's tree edit distance algorithm
        :return:
        """

        # Start to do comparison between the mutant test and its seed test

        # Flag variable
        are_all_view_diffs_contained = True

        for (from_state_index_of_aligned_states_of_seed_test, from_state_of_seed_test,
             from_state_utg_state_id_of_seed_test,
             to_state_index_of_aligned_states_of_seed_test, to_state_of_seed_test,
             to_state_utg_state_id_of_seed_test) in \
                comparable_states_of_seed_test:

            print("[Now, compute the GUI differences of two comparable states %d and %d:]"
                  % (from_state_utg_state_id_of_seed_test, to_state_utg_state_id_of_seed_test))

            # compute the GUI tree edit distance for the state pair of seed test
            gui_page_difference_of_seed_test = \
                GUITestCase.compute_gui_tree_edit_distance(from_state_utg_state_id_of_seed_test,
                                                           from_state_of_seed_test,
                                                           to_state_utg_state_id_of_seed_test,
                                                           to_state_of_seed_test,
                                                           config_script)

            for (from_state_index_of_aligned_states_of_mutant_test, from_state_of_mutant_test,
                 from_state_utg_state_id_of_mutant_test,
                 to_state_index_of_aligned_states_of_mutant_test, to_state_of_mutant_test,
                 to_state_utg_state_id_of_mutant_test) \
                    in comparable_states_of_mutant_test:

                if from_state_index_of_aligned_states_of_mutant_test == from_state_index_of_aligned_states_of_seed_test and \
                        to_state_index_of_aligned_states_of_mutant_test == to_state_index_of_aligned_states_of_seed_test:
                    # get the corresponding state pair of mutant test

                    if DeviceState.are_comparable_states(from_state_of_seed_test, from_state_of_mutant_test):
                        # make sure they are comparable

                        # compute the GUI tree edit distance for the matched state pair w.r.t the seed test
                        gui_page_difference_of_mutant_test = \
                            GUITestCase.compute_gui_tree_edit_distance(from_state_utg_state_id_of_mutant_test,
                                                                       from_state_of_mutant_test,
                                                                       to_state_utg_state_id_of_mutant_test,
                                                                       to_state_of_mutant_test,
                                                                       config_script)

                        is_contained, unmatched_view_diffs_of_seed_test, unmatched_view_diffs_of_mutant_test = \
                            GUITestCase.check_view_diffs_containment(gui_page_difference_of_seed_test,
                                                                     gui_page_difference_of_mutant_test)

                        if not is_contained:
                            are_all_view_diffs_contained = False

                            # set checking result
                            self.checking_result.add_unmatched_views(unmatched_view_diffs_of_seed_test,
                                                                     unmatched_view_diffs_of_mutant_test)
                            # end

                            # annotate the inconsistent view with blue color
                            self.annotate_inconsistent_view_diffs(from_state_utg_state_id_of_seed_test,
                                                                  to_state_utg_state_id_of_seed_test,
                                                                  from_state_utg_state_id_of_mutant_test,
                                                                  to_state_utg_state_id_of_mutant_test,
                                                                  unmatched_view_diffs_of_seed_test,
                                                                  unmatched_view_diffs_of_mutant_test)

                        # there only exists one-to-one mapping, so it is safe to stop when we find one
                        break

        if not are_all_view_diffs_contained:

            # set semantic error if NOT all view differences are contained
            self.has_semantic_error = True

            # set checking result
            self.checking_result.set_semantic_checking_result(True)
            # end
        else:
            self.has_semantic_error = False

    @staticmethod
    def compute_gui_tree_edit_distance(utg_state_id_of_from_state: int,
                                       from_state: DeviceState,
                                       utg_state_id_of_to_state: int,
                                       to_state: DeviceState,
                                       config_script: ConfigurationScript):

        """
        Compute the tree edit distance
        :param utg_state_id_of_from_state:
        :param from_state:
        :param utg_state_id_of_to_state:
        :param to_state:
        :param config_script:
        :return:
        """

        gui_page_difference: List[ViewDifference] = []

        # check whether some views' children order should be ignored according to the configuration script
        views_with_children_order_ignored = \
            config_script.get_views_with_children_order_ignored(from_state.foreground_activity) \
                if config_script is not None else None

        # convert the state's view tree into a brace string format
        brace_string_of_from_state, _ = \
            from_state.tree_to_brace_string(from_state.views[0],
                                            view_dicts_with_children_order_ignored=views_with_children_order_ignored)
        brace_string_of_to_state, _ = \
            to_state.tree_to_brace_string(to_state.views[0],
                                          view_dicts_with_children_order_ignored=views_with_children_order_ignored)

        # convert the brace string into a Tree (input format of apted algo.)
        tree_of_from_state = Tree.from_text(brace_string_of_from_state)
        tree_of_to_state = Tree.from_text(brace_string_of_to_state)

        # compute the tree mapping between the WHOLE trees of from_state and to_state
        apted = APTED(tree_of_from_state, tree_of_to_state)
        # The mapping relation is the by-product of computing tree edit distance.
        mapping = apted.compute_edit_mapping()

        # compute the minimal edit mapping between two trees.
        # There might be multiple minimal edit mappings. This option computes only one of them.
        # Each (value1, value2) represents the edit operations. n and m are postorder IDs (beginning with 1) of
        #   nodes in the left-hand and the right-hand trees respectively.
        #       n->m - rename node n to m
        #       n->0 - delete node n
        #       0->m - insert node m
        node_1, node_2 = apted.it1.node_info, apted.it2.node_info

        for node1, node2 in mapping:
            # value1 and value2 represent the tree node id (in postorder) in the tree1 and tree2, respectively
            value1 = node_1[id(node1)].post_ltr + 1 if node1 else 0
            value2 = node_2[id(node2)].post_ltr + 1 if node2 else 0
            # print(value1, "->", value2)

            if value1 != 0 and value2 == 0:
                # this is a delete operation

                # get the view dict
                view_dict_of_from_state: Dict = from_state.get_view_dict_by_postorder_view_id(value1)

                if config_script is not None and \
                        config_script.is_ignored_view_diff(from_state.foreground_activity,
                                                           view_dict_of_from_state, None):
                    # ignore the view difference if the view is ignored
                    continue

                view_difference = ViewDifference(utg_state_id_of_from_state, from_state,
                                                 utg_state_id_of_to_state, to_state,
                                                 view_dict_of_from_state,  # from_view
                                                 None,  # to_view
                                                 ViewDifference.VIEW_DELETE_OPERATION)

                print("delete operation: (%s, -)" %
                      DeviceState.get_view_text_sensitive_signature(view_dict_of_from_state))

                # print("\t from_state(%s) -> to_state(%s)" % (from_state.state_str, to_state.state_str))

                gui_page_difference.append(view_difference)

            elif value1 == 0 and value2 != 0:
                # this is an insert operation

                # get the view dict
                view_dict_of_to_state: Dict = to_state.get_view_dict_by_postorder_view_id(value2)

                if config_script is not None and \
                        config_script.is_ignored_view_diff(to_state.foreground_activity,
                                                           None, view_dict_of_to_state):
                    # ignore the view difference if the view is ignored
                    continue

                view_difference = ViewDifference(utg_state_id_of_from_state, from_state,
                                                 utg_state_id_of_to_state, to_state,
                                                 None,  # from_view
                                                 view_dict_of_to_state,  # to_view
                                                 ViewDifference.VIEW_NEW_OPERATION)

                print("insert operation: (-, %s)" %
                      DeviceState.get_view_text_sensitive_signature(view_dict_of_to_state))

                # print("\t from_state(%s) -> to_state(%s)" % (from_state.state_str, to_state.state_str))

                gui_page_difference.append(view_difference)

            else:
                # This condition must hold: value1 != 0 and value2 != 0:
                #       value1 == value2 or value1 != value2

                # We need to check whether this is an indeed change operation
                # If the two views are different, then this is a change operation
                view_dict_of_from_state = from_state.get_view_dict_by_postorder_view_id(value1)
                view_dict_of_to_state = to_state.get_view_dict_by_postorder_view_id(value2)

                if config_script is not None and \
                        config_script.is_ignored_view_diff(from_state.foreground_activity,
                                                           view_dict_of_from_state,
                                                           view_dict_of_to_state):
                    # ignore the view difference if the view is ignored
                    continue

                if DeviceState.is_view_different(view_dict_of_from_state, view_dict_of_to_state):
                    view_difference = ViewDifference(utg_state_id_of_from_state,
                                                     from_state,
                                                     utg_state_id_of_to_state,
                                                     to_state,
                                                     view_dict_of_from_state,  # from_view
                                                     view_dict_of_to_state,  # to_view
                                                     ViewDifference.VIEW_CHANGE_OPERATION)

                    print("change operation: (%s, %s)" %
                          (DeviceState.get_view_text_sensitive_signature(view_dict_of_from_state),
                           DeviceState.get_view_text_sensitive_signature(view_dict_of_to_state)))

                    # print("\t from_state(%s) -> to_state(%s)" % (from_state.state_str, to_state.state_str))

                    gui_page_difference.append(view_difference)

        return gui_page_difference

    def dump_execution_status(self, seed_test):

        # set the checking result
        self.checking_result = CheckingResult(seed_test.test_id, self.test_id, self.insert_start_position,
                                              is_faithfully_replayed=self.is_faithfully_replayed,
                                              is_fully_replayed=self.is_fully_replayed,
                                              unreplayable_utg_event_ids_prefix=self.unreplayable_utg_event_ids_prefix,
                                              has_crash_error=self.has_crash,
                                              crash_confidence=self.crash_confidence
                                              )
        self.dump_checking_result()

    def dump_checking_result(self):

        if not self.checking_result:
            return

        # dump checking result
        for ext in 'js', 'json':
            with open(os.path.join(self.test_output_dir, "checking_result.{}".format(ext)), "w") as f:
                if ext == 'js':
                    f.write('let checking_result = ')
                json.dump(self.checking_result.to_dict(self.test_output_dir), f, indent=2)
        # end

    def do_oracle_checking(self, seed_test: 'GUITestCase', config_script=None, gui_page_types_info=None):
        """
        check the consistency of gui differences between the current (seed) test and mutant test
        :param seed_test:
        :param config_script:
        :param gui_page_types_info:
        :return:
        """

        self.dump_execution_status(seed_test)

        if len(self.event_logs) > 0 and self.event_logs[-1].is_inserted_event is False:
            # Only do oracle checking if the mutant test's execution reach at least one event
            #   after the insertion position.

            # compute comparable states for the mutant test
            print("compute comparable states for the mutant test:")
            aligned_states_of_mutant_test = GUITestCase.align_states_for_comparison(self,
                                                                                    self.insert_start_position)
            comparable_states_of_mutant_test = \
                self.compute_comparable_states(aligned_states_of_mutant_test, gui_page_types_info)

            # compute comparable states for the seed test
            print("compute comparable states for the seed test:")
            aligned_states_of_seed_test = GUITestCase.align_states_for_comparison(seed_test,
                                                                                  self.insert_start_position)
            comparable_states_of_seed_test = \
                seed_test.compute_comparable_states(aligned_states_of_seed_test, gui_page_types_info)

            # In the following, we start to do oracle checking
            if len(comparable_states_of_seed_test) == 0 or len(comparable_states_of_mutant_test) == 0:
                # Return if no gui pages can be compared, set the result as NORMAL
                # Because, in this case, we do not have the opportunity to do oracle checking.
                self.logger.warning("comparable GUIs are empty, do not need to do oracle checking.")
                self.has_semantic_error = False

            else:

                # compare the mutant test w.r.t its seed test
                self.compare_mutant_and_seed_test(comparable_states_of_mutant_test,
                                                  comparable_states_of_seed_test,
                                                  aligned_states_of_mutant_test,
                                                  aligned_states_of_seed_test,
                                                  config_script)

        self.dump_checking_result()

    @staticmethod
    def align_states_for_comparison(gui_test: 'GUITestCase', insertion_position: int):
        """
        Align the states of a given test case for state comparison.
            First, we use None as a special flag to denote the insertion position. Later, the state comparison will
                be conducted between the states before and after this special flag.
            Second, we skip any additional states due to the inserted events in the mutant test.

        In this way, we can align the states for oracle checking. The checking becomes more flexible and robust.

            Seed Test:    T0  ->  T1  -> None -> T2
                          |       |              |
            Mutant Test:  T0' ->  T1' -> None -> T2'

        The returned result is a list of states for comparision.
            which is in the form of [(State_1, State1's id in the test utg),
                                        ...,
                                        None (the inserting position),
                                        ...,
                                     (State_N, State_N's id in the test utg]

        :param gui_test: the gui test
        :param insertion_position: the insertion position of the independent trace
        :return: List[DeviceState, int]
        """
        valid_states = []

        if gui_test.test_tag == TEST_TAG_SEED_TEST:
            # handle seed test
            event_logs = gui_test.event_logs
            for i in range(0, len(event_logs)):
                event_log = event_logs[i]

                valid_states.append((event_log.from_state, event_log.utg_event_id - 1))

                # add insertion flag after the state has been added
                if i == insertion_position:
                    # use None as an insertion flag
                    valid_states.append(None)

                if i == len(event_logs) - 1:
                    # special handle on the last event log
                    valid_states.append((event_log.to_state, event_log.utg_event_id))

        elif gui_test.test_tag == TEST_TAG_MUTANT_TEST or gui_test.test_tag == TEST_TAG_DYNAMIC_TEST:
            # handle the mutant test
            event_logs = gui_test.event_logs

            for i in range(0, len(event_logs)):
                event_log = event_logs[i]

                if i == 0:
                    # special handle on the first event log
                    valid_states.append((event_log.from_state, event_log.utg_event_id - 1))

                # # add insertion flag after the state has been added
                if i == insertion_position:
                    # use None as an insertion flag
                    valid_states.append(None)

                if event_log.is_inserted_event:
                    # do not add the states due to inserted events
                    pass
                else:
                    valid_states.append((event_log.to_state, event_log.utg_event_id))
        else:
            pass

        return valid_states

    def __get_new_screenshot_path(self, original_screenshot_path: str):
        """
        get a new screenshot path
        :param original_screenshot_path: the original screenshot path
        :return: str, the new screenshot path
        """

        file_name, file_extension = os.path.splitext(original_screenshot_path)
        # increase the unique id
        self.unique_id += 1
        if self.test_id not in os.path.abspath(original_screenshot_path):
            # This is a reused screenshot if the screenshot file path does not contain the mutant id (i.e., the
            #   screenshot is not under the mutant's own output directory).
            # In this case, we create a new screenshot under the mutant's own output directory to avoid affecting
            #   the original screenshot file.
            file_base_name = os.path.basename(file_name)
            new_screenshot_path = os.path.join(self.test_output_dir, "states",
                                               file_base_name + "_" + str(self.unique_id) + file_extension)
        else:
            # This is the mutant's own screenshot. Then, we just create a new screenshot under the original directory.
            new_screenshot_path = file_name + "_" + str(self.unique_id) + file_extension

        return new_screenshot_path

    def __get_annotation_info_of_inconsistent_view_diff(self, view_diff: ViewDifference, test_tag: str,
                                                        annotation_info: Dict[str, str]) -> Dict[str, str]:
        """
        Annotate the given view diff (i.e., view_diff) on the corresponding screenshot.

        Some notes:
        1. To find the corresponding screenshot, we need to locate the corresponding state that this view diff
        belongs to.
        2. When locating this corresponding state, we need consider:
            (1) the view operation of this view diff
            (2) which test utg (by using test_tag) this view diff is associated with
        3. We reuse annotation_info is at each method call, because we need to annotate all view diffs
            on the same screenshot

        :param view_diff: the view diff to annotate
        :param test_tag: the test that this view diff belongs to
        :param annotation_info: the annotation info
        :return: Dict[str, str], the annotation info (str1: state_str, str2: the screenshot path)
        """

        if view_diff.operation == ViewDifference.VIEW_DELETE_OPERATION:

            # get the device state where this view diff happens
            device_state_of_view = view_diff.from_state

            # get the device state from the utg where this view dict belongs to
            state_str = device_state_of_view.state_str + test_tag
            device_state_of_view_in_test_utg = self.utg.get_node_by_state_str(state_str)

            if state_str in annotation_info:
                # draw on the same screenshot if the screenshot path is already in the annotation info
                #   (which means the screenshot has been drawn before)
                new_screenshot_path_of_view = annotation_info[state_str]
                original_screenshot_path_of_view = new_screenshot_path_of_view  # set them same
            else:
                # draw on an copy of the original screenshot (which will create a new screenshot path)
                original_screenshot_path_of_view = device_state_of_view_in_test_utg.screenshot_path
                new_screenshot_path_of_view = self.__get_new_screenshot_path(original_screenshot_path_of_view)

            # get the view dict to draw
            view_dict = view_diff.from_view
            device_state_of_view_in_test_utg.annotate_view_on_screenshot(original_screenshot_path_of_view,
                                                                         new_screenshot_path_of_view,
                                                                         [view_dict],
                                                                         COLOR_RED_TUPLE)
            # update the annotation info
            annotation_info[state_str] = new_screenshot_path_of_view

            return annotation_info

        elif view_diff.operation == ViewDifference.VIEW_NEW_OPERATION:

            # get the device state where this view diff happens
            device_state_of_view = view_diff.to_state

            # get the device state from the utg where this view dict belongs to
            state_str = device_state_of_view.state_str + test_tag
            device_state_of_view_in_test_utg = self.utg.get_node_by_state_str(state_str)

            if state_str in annotation_info:
                # draw on the same screenshot if the screenshot path is already in the annotation info
                #   (which means the screenshot has been drawn before)
                new_screenshot_path_of_view = annotation_info[state_str]
                original_screenshot_path_of_view = new_screenshot_path_of_view  # set them same
            else:
                # draw on an copy of the original screenshot (which will create a new screenshot path)
                original_screenshot_path_of_view = device_state_of_view_in_test_utg.screenshot_path
                new_screenshot_path_of_view = self.__get_new_screenshot_path(original_screenshot_path_of_view)

            # get the view dict to draw
            view_dict = view_diff.to_view
            device_state_of_view_in_test_utg.annotate_view_on_screenshot(original_screenshot_path_of_view,
                                                                         new_screenshot_path_of_view,
                                                                         [view_dict],
                                                                         COLOR_RED_TUPLE)
            # update the annotation info
            annotation_info[state_str] = new_screenshot_path_of_view

            return annotation_info

        else:
            # view_diff.operation == ViewDifference.VIEW_CHANGE_OPERATION:

            device_state_of_view_1 = view_diff.from_state
            state_str = device_state_of_view_1.state_str + test_tag
            device_state_of_view_1_in_test_utg = self.utg.get_node_by_state_str(state_str)

            if state_str in annotation_info:
                # draw on the same screenshot if the screenshot path is already in the annotation info
                #   (which means the screenshot has been drawn before)
                new_screenshot_path_of_view_1 = annotation_info[state_str]
                original_screenshot_path_of_view_1 = new_screenshot_path_of_view_1  # set them same
            else:
                # draw on an copy of the original screenshot
                original_screenshot_path_of_view_1 = device_state_of_view_1_in_test_utg.screenshot_path
                new_screenshot_path_of_view_1 = self.__get_new_screenshot_path(original_screenshot_path_of_view_1)

            # annotate view diff
            view_dict_1 = view_diff.from_view
            device_state_of_view_1_in_test_utg.annotate_view_on_screenshot(original_screenshot_path_of_view_1,
                                                                           new_screenshot_path_of_view_1,
                                                                           [view_dict_1],
                                                                           COLOR_RED_TUPLE)
            # update the annotation info
            annotation_info[state_str] = new_screenshot_path_of_view_1

            ####

            device_state_of_view_2 = view_diff.to_state
            state_str = device_state_of_view_2.state_str + test_tag
            device_state_of_view_2_in_test_utg = self.utg.get_node_by_state_str(state_str)

            if state_str in annotation_info:
                # draw on the same screenshot if the screenshot path is already in the annotation info
                #   (which means the screenshot has been drawn before)
                new_screenshot_path_of_view_2 = annotation_info[state_str]
                original_screenshot_path_of_view_2 = new_screenshot_path_of_view_2  # set them same
            else:
                # draw on an copy of the original screenshot
                original_screenshot_path_of_view_2 = device_state_of_view_2_in_test_utg.screenshot_path
                new_screenshot_path_of_view_2 = self.__get_new_screenshot_path(original_screenshot_path_of_view_2)

            # annotate view diff
            view_dict_2 = view_diff.to_view
            device_state_of_view_2_in_test_utg.annotate_view_on_screenshot(original_screenshot_path_of_view_2,
                                                                           new_screenshot_path_of_view_2,
                                                                           [view_dict_2],
                                                                           COLOR_RED_TUPLE)
            # update the annotation info
            annotation_info[state_str] = new_screenshot_path_of_view_2

            return annotation_info

    def annotate_inconsistent_view_diffs(self,
                                         utg_state_id_of_from_state_seed_test,
                                         utg_state_id_of_to_state_of_seed_test,
                                         utg_state_id_of_from_state_of_mutant_test,
                                         utg_state_id_of_to_state_of_mutant_test,
                                         inconsistent_view_diffs_of_seed_test: List[ViewDifference],
                                         inconsistent_view_diffs_of_mutant_test: List[ViewDifference]):
        """
        annotate the inconsistent view on the seed test and the mutant test
        :return:
        """

        if len(inconsistent_view_diffs_of_seed_test) == 0:
            # return if the seed test does not have inconsistent view diffs
            return

        self.gui_semantic_error_id += 1
        utg_js_file_name = "utg_" + str(self.gui_semantic_error_id) + ".js"
        utg_json_file_name = "utg_" + str(self.gui_semantic_error_id) + ".json"

        # Step 1: annotate the screenshots
        # summary of transition annotation info
        #   str1: the state str,
        #   str2: the new screenshot path
        screenshot_path_annotation_info: Dict[str, str] = {}

        for view_diff in inconsistent_view_diffs_of_seed_test:
            screenshot_path_annotation_info = \
                self.__get_annotation_info_of_inconsistent_view_diff(view_diff,
                                                                     TEST_TAG_SEED_TEST,
                                                                     screenshot_path_annotation_info)
            view_diff.annotated_utg_json_file_name = utg_json_file_name

        for view_diff in inconsistent_view_diffs_of_mutant_test:
            screenshot_path_annotation_info = \
                self.__get_annotation_info_of_inconsistent_view_diff(view_diff,
                                                                     TEST_TAG_DYNAMIC_TEST,
                                                                     screenshot_path_annotation_info)
            view_diff.annotated_utg_json_file_name = utg_json_file_name

        # Step 2: annotate the transitions
        # summary of transition annotation info
        #   str: the target test tag of states,
        #   List[int]: the list of transition ids that corresponding to str's states
        transition_annotation_info: Dict[str, List[int]] = {}

        # Step 2.1:  annotate the transitions of seed test
        annotated_transition_ids_of_seed_test = [i for i in
                                                 range(utg_state_id_of_from_state_seed_test + 1,
                                                       utg_state_id_of_to_state_of_seed_test + 1)]
        transition_annotation_info[TEST_TAG_SEED_TEST] = annotated_transition_ids_of_seed_test

        # Step 2.2:  annotate the transitions of (dynamically executed) mutant test
        annotated_transition_ids_of_mutant_test = [i for i in
                                                   range(utg_state_id_of_from_state_of_mutant_test + 1,
                                                         utg_state_id_of_to_state_of_mutant_test + 1)]
        transition_annotation_info[TEST_TAG_DYNAMIC_TEST] = annotated_transition_ids_of_mutant_test

        # Step 3: generate test report for each semantic error

        # Step 3-1: dump the annotation info into "utg_x.js"
        self.utg.output_utg_for_gui_test(self.test_output_dir,
                                         utg_js_file_name=utg_js_file_name,
                                         utg_json_file_name=utg_json_file_name,
                                         insert_start_position=self.insert_start_position,
                                         independent_trace_len=self.independent_trace_len,
                                         screenshot_path_annotation_info=screenshot_path_annotation_info,
                                         transition_annotation_info=transition_annotation_info)

        # Step 3-2: create the html report "index_x.html"
        original_html_file_path = pkg_resources.resource_filename("droidbot", "resources/index_aligned.html")

        new_html_file_name = os.path.basename(original_html_file_path).replace(
            '.html',
            '_{}.html'.format(self.gui_semantic_error_id))
        new_html_file_path = os.path.join(self.test_output_dir, new_html_file_name)

        if os.path.exists(original_html_file_path):
            # should always be true, just double check
            shutil.copyfile(original_html_file_path, new_html_file_path)
            replace_file(new_html_file_path, lambda s: s.replace('utg.js', utg_js_file_name))

        return utg_json_file_name

    @staticmethod
    def check_view_diffs_containment(view_diffs_of_seed_test: List[ViewDifference],
                                     view_diffs_of_mutant_test: List[ViewDifference]):
        """
        Check the containment relation between the seed test's view diffs and the mutant test's view diffs, and
        return the symmetric difference between them.

        Note the seed test's view diffs and the mutant test's view diffs must come from aligned, comparable gui pages.
        Let view_diffs_of_seed_test be Delta, view_diffs_of_mutant_test be Delta', then we check:
            ``Delta is contained in Delta'?``

        In implementation, we compute the string distance between the context strings of two view diffs to decide
            whether they are matched or not.

        :param view_diffs_of_seed_test:  the view differences of two comparable pages of seed test
        :param view_diffs_of_mutant_test: the view differences of two comparable pages of mutant test
        :return: boolean, List[ViewDifference], List[ViewDifference]
        """
        print("========GUI Difference Analysis=============")
        # list of unmatched view diffs of the seed test
        unmatched_view_diffs_of_seed_test: List[ViewDifference] = []
        # list of unmatched view diffs of the mutant test
        unmatched_view_diffs_of_mutant_test: List[ViewDifference] = []

        for view_diff in view_diffs_of_mutant_test:
            unmatched_view_diffs_of_mutant_test.append(view_diff)

        for view_diff_of_seed_test in view_diffs_of_seed_test:

            # list of unmatched view diffs of the mutant test w.r.t the given view diffs of the seed test
            #   int: the edit distance
            #   ViewDifference: the view difference
            #   str: context_string_1
            #   str: context_string_2
            distances_of_unmatched_view_diffs: List[Tuple[float, ViewDifference, str, str]] = []

            print("-------Begin Iteration------------")

            # check whether view_diff of seed_test can match with some view_diff of mutant test
            context_string_1_of_view_diff_of_seed_test, context_string_2_of_view_diff_of_seed_test = \
                view_diff_of_seed_test.get_context_string_of_view_diff()

            is_matched = False

            # the view diff of mutant test that matched with that of seed test
            matched_view_diff_of_mutant_test = None

            # Note we will delete the view diff that was matched with that of the seed test, and only search within the
            #   remaining unmatched view diffs in "unmatched_view_diffs_of_mutant_test"
            # We do this to avoid the case where one view diff in the mutant test was matched more than one time.
            for view_diff_of_mutant_test in unmatched_view_diffs_of_mutant_test:

                context_string_1_of_view_diff_of_mutant_test, context_string_2_of_view_diff_of_mutant_test = \
                    view_diff_of_mutant_test.get_context_string_of_view_diff()

                # compute the string differences of the two context trees
                similarity_ratio_1 = Levenshtein.ratio(context_string_1_of_view_diff_of_seed_test,
                                                       context_string_1_of_view_diff_of_mutant_test)

                similarity_ratio_2 = Levenshtein.ratio(context_string_2_of_view_diff_of_seed_test,
                                                       context_string_2_of_view_diff_of_mutant_test)

                similarity = (similarity_ratio_1 + similarity_ratio_2) / 2.0

                if similarity == 1.0:

                    is_matched = True
                    matched_view_diff_of_mutant_test = view_diff_of_mutant_test
                    break
                else:

                    distances_of_unmatched_view_diffs.append((similarity, view_diff_of_mutant_test,
                                                              context_string_1_of_view_diff_of_mutant_test,
                                                              context_string_2_of_view_diff_of_mutant_test))
                    # print("distance: %d" % int(ted))

            # print("end matching")

            if is_matched:
                # remove the matched view_diff if contained
                if matched_view_diff_of_mutant_test in unmatched_view_diffs_of_mutant_test:
                    unmatched_view_diffs_of_mutant_test.remove(matched_view_diff_of_mutant_test)

            else:
                # not matched
                unmatched_view_diffs_of_seed_test.append(view_diff_of_seed_test)

                # print("seed test's view diff to match:\n %s" % str(view_diff_of_seed_test))
                # print("\t [view diff's context]:\n\t (%s, \n\t %s)" % (context_string_1_of_view_diff_of_seed_test,
                #                                                        context_string_2_of_view_diff_of_seed_test))
                # self.oracle_checking_logger.dump_log("\t [view diff's context]:\n\t (%s, \n\t %s)" %
                #                                      (context_string_1_of_view_diff_of_seed_test,
                #                                       context_string_2_of_view_diff_of_seed_test))
                print("** Unmatched! **")

                # TODO can be removed, just for debugging, print the top 3 unmatched view diffs from mutant test
                # top_n = 3
                # print("   List of top %d unmatched views from mutant test with least distances: " % top_n)
                # self.oracle_checking_logger.dump_log("   List of top %d unmatched views with least distance:" % top_n)
                # sorted_unmatched_view_diffs = sorted(distances_of_unmatched_view_diffs, key=lambda x: x[0])
                # for i in range(0, min(top_n, len(sorted_unmatched_view_diffs))):
                #     print("\t distance: %f\n\t\t, %s" %
                #           (sorted_unmatched_view_diffs[i][0], sorted_unmatched_view_diffs[i][1]))
                #     print("\t  [view diff's context string]:\n\t (%s, \n\t %s)" % (sorted_unmatched_view_diffs[i][2],
                #                                                                    sorted_unmatched_view_diffs[i][3]))
                #     self.oracle_checking_logger.dump_log("\t ---- unmatched view diff %d ----" % i)
                #     self.oracle_checking_logger.dump_log("\t distance: %f\n\t\t, %s" %
                #                                          (sorted_unmatched_view_diffs[i][0],
                #                                           sorted_unmatched_view_diffs[i][1]))
                #     self.oracle_checking_logger.dump_log("\t  [view diff's context string]:\n\t (%s, \n\t %s)" %
                #                                          (sorted_unmatched_view_diffs[i][2],
                #                                           sorted_unmatched_view_diffs[i][3]))
                #     self.oracle_checking_logger.dump_log("\t ---- End unmatched view diff %d ----" % i)

            print("---End Iteration--------")

        if len(unmatched_view_diffs_of_seed_test) == 0:
            is_contained = True
        else:
            is_contained = False

        return is_contained, unmatched_view_diffs_of_seed_test, unmatched_view_diffs_of_mutant_test
