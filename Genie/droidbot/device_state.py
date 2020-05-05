import copy
import re
from datetime import datetime
from typing import List, Dict, Set, Tuple
import shutil

import Levenshtein
import math
import os
import sys
import logging
import queue
import cv2
from random import randint

from .utils import md5, safe_re_match
from .input_event import TouchEvent, LongTouchEvent, ScrollEvent, SetTextEvent, InputEvent

# state type
STATE_TYPE_BY_SCRIPT = "__only_script"
STATE_TYPE_BY_EXPLORE = "__only_exploration"
STATE_TYPE_BY_BOTH = "__script_and_exploration"

# cv2 color
COLOR_BLUE_TUPLE = (255, 0, 0)
COLOR_RED_TUPLE = (0, 0, 255)
COLOR_BLUE = "blue"
COLOR_RED = "red"


class CurrentStateNoneException(Exception):
    pass


class DeviceState(object):
    """
    the state of the current device
    """

    # Utg abstraction strategy
    UTG_ABSTRACTION_BY_CONTENT_FREE = "content_free"
    UTG_ABSTRACTION_BY_STRUCTURE_FREE = "structure_free"

    unique_state_id = 0

    # unique id for naming the event view file
    unique_event_view_file_id = 0

    # include "content_description" when representing a GUI view (decide the granularity of the view abstraction) ?
    include_content_desc = True

    def __init__(self, device, views, foreground_activity, activity_stack, background_services,
                 window_stack=None, app_package_name=None,
                 tag=None, screenshot_path=None, json_state_path=None, state_str=None, structure_str=None,
                 first_state=False, last_state=False, utg_abstraction_strategy=None, enable_parse_view_tree=True,
                 view_context_str_backtrack_level=None):

        self.logger = logging.getLogger(self.__class__.__name__)

        self.device = device
        self.foreground_activity = foreground_activity
        self.activity_stack = activity_stack if isinstance(activity_stack, list) else []
        self.background_services = background_services

        # Windows do not have any unique number or string to identify them :(
        #   In this case, we cannot use the window stack to precisely infer which window we are on.
        #   But we can confidently conclude we are on different windows by comparing len(window_stack) when we are on
        #       the same activity.
        self.window_stack: Dict = window_stack if isinstance(window_stack, dict) else {}

        self.app_package_name = app_package_name
        self.gui_page_type = None

        if tag is None:
            from datetime import datetime
            tag = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            # append with a unique state id
            tag += '-' + str(DeviceState.unique_state_id)
            DeviceState.unique_state_id += 1
        self.tag = tag
        self.screenshot_path = screenshot_path  # the file path of screenshot
        self.json_state_path = json_state_path  # the json file path of state
        self.first_state = first_state
        self.last_state = last_state

        # exclude the views in the primary view if the drawerlayout is opened.
        #   This set stores all the view ids in the primary view
        self.__drawerlayout_exclude_primary_content_view_ids = set()
        self.__drawerlayout_primary_content_view_id = None
        # the flag indicating whether the drawer view is opened on top of main activity
        self.__drawer_view_is_opened = False
        # Is the current state a DatePicker or TimePicker page?
        self.is_date_time_picker_page = False

        self.view_context_str_backtrack_level = view_context_str_backtrack_level

        # views, view_tree are the two important objects to understand
        # self.views is a list of dict, and each dict is a view.
        #       The view id corresponds to its position (index) in self.views.
        # Note: we need to record any GUI analysis information on self.views rather than self.view_tree as
        #        only self.views will be serialized!!!
        self.views: List[Dict] = self.__parse_views(views)
        # self.view_tree is a tree representation of self.views
        self.view_tree = {}
        self.__assemble_view_tree(self.view_tree, self.views)
        self.__generate_view_strs()

        # infer independent properties from the view tree [This module is under test]
        if enable_parse_view_tree:
            self.logger.info("parse the current state's view tree to annotate independent view properties!!!")
            self.__parse_view_tree(self.view_tree, self.screenshot_path)

        # the mapping between postorder view ids and original view ids (in self.views)
        # The index of this list corresponds to the postorder view id so that we can visit the mapping relation in O(1).
        #   Note that We pad {-1: -1} as the first element at the ZERO index since postorder_view_id starts from 1.
        # Each list element is a dict, represented as {postorder_view_id: original_view_id}.
        # This data structure is used for computing the tree edit distance between two view trees.
        self.mapping_between_postorder_and_original_view_ids: List[Dict[int, int]] = [{-1: -1}]

        # if we follow the structure of self.views, we can simply reuse the current implementation
        # of these three methods
        self.state_str = state_str if state_str is not None else self.__get_state_str()

        # # Two different utg abstraction strategies
        # if utg_abstraction_strategy == DeviceState.UTG_ABSTRACTION_BY_CONTENT_FREE:
        #     self.structure_str = self.__get_content_free_state_str()
        #     # structure_str if structure_str is not None else self.__get_content_free_state_str()
        # else:
        #     # the case: utg_abstraction_strategy == DeviceState.UTG_ABSTRACTION_BY_STRUCTURE_FREE
        #     self.structure_str = self.__get_structure_free_state_str()
        self.structure_str = self.__get_content_free_state_str()

        self.search_content = self.__get_search_content()
        self.possible_events = None

        # The code below is not used now
        # add a flag to denote whether the state is explored by scripts or automated UI exploration
        self.state_type = None
        # The paths that start from the entry state and reach this state (expected to be feasible)
        # Each path consists of a sequence of events.
        # TODO we may need to consider use set(), but seems need implement hash
        self.execution_path_events_set_from_entry_state = []
        # the last path events and corresponding states
        self.last_path_events_from_entry_state = []
        self.last_path_states_from_entry_state = []

    #
    def __deepcopy__(self, memo):
        """
        Override deepcopy for DeviceState
        https://stackoverflow.com/questions/1500718/how-to-override-the-copy-deepcopy-operations-for-a-python-object
        https://docs.python.org/3/library/copy.html
        :param memo:
        :return:
        """
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        # print(self.__dict__.items())
        for k, v in self.__dict__.items():
            # print(k)
            if k in ["logger", "device"]:
                # do not deepcopy
                setattr(result, k, copy.deepcopy(None, memo=memo))
            else:
                setattr(result, k, copy.deepcopy(v, memo=memo))
        return result

    #
    @staticmethod
    def deepcopy_device_state(device_state, device):
        if device_state is None:
            return None
        temp_state = copy.deepcopy(device_state)
        temp_state.recover_after_deep_copy(device)
        return temp_state

    # recover "device" and "logger"
    def recover_after_deep_copy(self, device):
        """
        Call this method right after __deepcopy__
        :param device:
        :return:
        """
        if self.logger is None:
            self.logger = logging.getLogger(self.__class__.__name__)
        if self.device is None:
            self.device = device

    def to_dict(self):
        state = {'tag': self.tag,
                 'state_str': self.state_str,
                 'state_str_content_free': self.structure_str,
                 'foreground_activity': self.foreground_activity,
                 'activity_stack': self.activity_stack,
                 'background_services': self.background_services,
                 'window_stack': self.window_stack,
                 'views': self.views}
        return state

    def to_json(self):
        import json
        return json.dumps(self.to_dict(), indent=2)

    #
    def __parse_views(self, raw_views):
        """
        parse the raw views

        This is a good place to do any customized checking before the device state is used.
        :param raw_views:   the raw views dumped from accessibility service
        :return:
        """
        views = []
        if not raw_views or len(raw_views) == 0:
            return views

        _handle_drawerlayout = True  # the flag indicating whether we handle drawerlayout
        _drawerlayout_bounds = []  # the bounds of drawerlayout
        _drawerlayout_child_ids = []  # the next-level child of drawerlayout

        # set sibling id for root node
        raw_views[0]['sibling_id'] = 0

        for view_dict in raw_views:
            # # Simplify resource_id
            # resource_id = view_dict['resource_id']
            # if resource_id is not None and ":" in resource_id:
            #     resource_id = resource_id[(resource_id.find(":") + 1):]
            #     view_dict['resource_id'] = resource_id
            # debug
            # print(view_dict)
            sibling_id = 0
            for child_id in view_dict['children']:
                if child_id < len(raw_views):
                    # check validity
                    raw_views[child_id]['sibling_id'] = sibling_id
                    sibling_id += 1

            # Customized checking 1: check whether drawer view is opened
            # handle ".widget.DrawerLayout" by removing its primary content view and keeping its drawer view
            if _handle_drawerlayout and (".widget.DrawerLayout" in view_dict['class']) and \
                    len(view_dict['children']) > 1:  # make sure that the drawer view is opened
                self.__drawer_view_is_opened = True
                _drawerlayout_bounds = list(view_dict['bounds'])
                _drawerlayout_child_ids = list(view_dict['children'])

            if _handle_drawerlayout and self.__drawer_view_is_opened:
                # the second coordinate of the child view is equal to that of the drawerlayout, then this child view
                #   is the primary content view rather than the drawer view
                if view_dict['temp_id'] in _drawerlayout_child_ids:
                    if view_dict['bounds'][1] == _drawerlayout_bounds[1]:
                        # change the "visible" property to False
                        view_dict['visible'] = False
                        self.__drawerlayout_primary_content_view_id = view_dict['temp_id']
                        # reset (we do not need to check drawer view anymore)
                        _handle_drawerlayout = False

            # Customized checking 2: is the current state a DatePicker or TimePicker page?
            #   A TimePicker page contains a specific view:
            #               {'resource_id': 'android:id/timePicker', 'class': 'android.widget.TimePicker'}
            #   A DatePicker page contains a specific view:
            #               {'resource_id': 'android:id/datePicker', 'class': 'android.widget.DatePicker'}
            if view_dict['resource_id'] == 'android:id/timePicker' and \
                    view_dict['class'] == 'android.widget.TimePicker':
                self.is_date_time_picker_page = True
            if view_dict['resource_id'] == 'android:id/datePicker' and \
                    view_dict['class'] == 'android.widget.DatePicker':
                self.is_date_time_picker_page = True

            views.append(view_dict)

            # Customized checking 3: annotate ignored (usually volatile) views
            if self.device.ignore_views is not None:
                if self.device.ignore_views.is_ignored_view_dict(self.foreground_activity, view_dict):
                    view_dict['is_ignored'] = True
                    self.recursive_annotate_ignored_views(views, view_dict)
                else:
                    view_dict['is_ignored'] = False
            else:
                # ensure the key 'is_ignored' always exists
                view_dict['is_ignored'] = False

        return views

    def ignore_views_in_device_state(self, ignored_views: dict):
        for view_key in ignored_views:
            ignored_view_dict = ignored_views[view_key]
            if ignored_view_dict['activity'] == self.foreground_activity:
                target_view = self.find_matched_view(ignored_view_dict)
                if target_view is not None and 'is_ignored' in target_view:
                    target_view['is_ignored'] = True

    def ignore_views_order_in_device_state(self, ignored_view_children_order: dict):
        for view_key in ignored_view_children_order:
            ignored_view_dict = ignored_view_children_order[view_key]
            if ignored_view_dict['activity'] == self.foreground_activity:
                target_view = self.find_matched_view(ignored_view_dict)
                if target_view is not None:
                    self.sort_children_views(target_view)

        # TODO handle other configs

    def recursive_annotate_ignored_views(self, views, view_dict):
        """
        Annotate the view_dict's parent view as ignored if the parent view is a non-actionable view wrapper and only
            has one child view (i.e., view_dict). This annotation is conducted recursively.

        :param views: current list of all views (the list is not fully updated)
        :param view_dict: the given view dict
        :return: None
        """
        parent_id = view_dict['parent']
        if 0 <= parent_id < len(views):
            parent_view = views[parent_id]
            if DeviceState.__is_non_actionable_wrapper(parent_view):
                # TODO the rule is non_actionable_wrapper (we are not sure this holds for every case)
                children_ids = parent_view['children']
                for child_id in children_ids:
                    if 0 <= child_id < len(views):
                        child_view = views[child_id]
                        if not child_view['is_ignored']:
                            # Stop if at least one child view is not ignored
                            return
                    else:
                        # Stop if at least one child view has not been added into views
                        return

                parent_view['is_ignored'] = True
                self.recursive_annotate_ignored_views(views, parent_view)

    def __assemble_view_tree(self, root_view, views):
        if not len(self.view_tree):  # bootstrap
            self.view_tree = copy.deepcopy(views[0])
            self.__assemble_view_tree(self.view_tree, views)
        else:
            children = list(enumerate(root_view["children"]))
            if not len(children):
                return
            for i, j in children:
                root_view["children"][i] = copy.deepcopy(self.views[j])
                self.__assemble_view_tree(root_view["children"][i], views)

    #
    def is_new_state(self, previous_state: 'DeviceState'):
        """
        check whether the current state is a new state w.r.t the previous state. Note these two states are connected
        with each other (i.e., previous_state -- (some event) --> current_state)

        A new state means it presents a new GUI page with interesting children views.
        The scenarios of a new state include:
            (1) The current state corresponds to a new activity on top of the previous activity
            (2) The current state corresponds to a new window/dialog on top of the previous state
                (within the same activity)
            (3)

        Specifically, we use activity_stack and window_stack to decide whether we are in some new states.

        :param previous_state:  the state before the current state
        :return: bool
        """
        if len(self.activity_stack) > len(previous_state.activity_stack):
            return True
        elif len(self.activity_stack) < len(previous_state.activity_stack):
            return False
        else:
            # the case: len(self.activity_stack) == len(previous_state.activity_stack):
            if len(self.window_stack) > len(previous_state.window_stack):
                return True
            elif len(self.window_stack) == len(previous_state.window_stack):

                if self.__drawer_view_is_opened and (not previous_state.__drawer_view_is_opened):
                    # check whether the drawer view is opened w.r.t the main view
                    # Fix issue #24
                    #   This condition covers the comparison between the main activity view and its drawer view.
                    #   These two views have the same length of window stack with the same activity name.
                    return True

                # This handles the remaining case:
                #   Two states have the same lengths of window stack (the window stack should be >=2 in this case)
                #   and in the same activity.
                #   We use a very simple heuristic to differentiate them by comparing the first level of children views.
                children_views_of_current_state = \
                    self.__get_sole_child_view_2(self.view_tree)['children']
                children_views_of_previous_state = \
                    previous_state.__get_sole_child_view_2(previous_state.view_tree)['children']

                if len(children_views_of_current_state) != len(children_views_of_previous_state):
                    # not comparable if the number of child views are not equal
                    return True
                else:
                    cnt = len(children_views_of_current_state)
                    for i in range(0, cnt):
                        child_view_of_current_state = children_views_of_current_state[i]
                        child_view_of_previous_state = children_views_of_previous_state[i]
                        if child_view_of_current_state['class'] != child_view_of_previous_state['class']:
                            # not comparable if the classes are different
                            return True
                return False

            else:
                return False

    # get the sole child (recursively)
    def __get_sole_child_view(self, view_tree_node):
        """
        If the current view has only one child view, then we go to that child view, and continue the search until
        we find one view who has more than one child views or has no child views.
        The effect is collapse the tree and skip over meaningless views (which are only used as a view wrapper)
        :param view_tree_node:
        :return:
        """
        node_ptr = view_tree_node
        if len(node_ptr['children']) == 1 and DeviceState.__is_non_actionable_wrapper(view_tree_node):
            node_ptr = node_ptr['children'][0]
            node_ptr = self.__get_sole_child_view(node_ptr)
            return node_ptr
        elif len(node_ptr['children']) > 1:
            return node_ptr
        else:  # len(node_ptr['children']) == 0, node_ptr is the leaf node
            return node_ptr

    def __get_sole_child_view_2(self, view_tree_node):
        """
        If the current view has only one child view, then we go to that child view, and continue the search until
        we find one view who has more than one child views or has no child views.

        The effect is collapse the tree and skip over meaningless views (which are only used as a view wrapper) from
        top to down.

        It finally returns a view tree node who has a set of meaningful children views (>=2 children views)

        The difference between this method with "__get_sole_child_view" is that we will directly exclude those invisible
            sibling views (visible=false, and len(children)=0, and not-actionable)

        :param view_tree_node:
        :return:
        """
        node_ptr = view_tree_node
        if len(node_ptr['children']) == 1 and DeviceState.__is_non_actionable_wrapper(view_tree_node):
            node_ptr = node_ptr['children'][0]
            node_ptr = self.__get_sole_child_view_2(node_ptr)
            return node_ptr
        elif len(node_ptr['children']) > 1:
            node_ptr_children_views = node_ptr['children']
            temp_views = []
            meet_actionable_views = False
            for child_view in node_ptr_children_views:
                if not DeviceState.__is_visible_view(child_view):
                    # skip it if the child view is an invisible, leaf and not actionable view (such view is meaningless)
                    continue

                if DeviceState.__is_actionable_view(child_view):
                    temp_views.append(child_view)
                    meet_actionable_views = True

                elif DeviceState.__contain_actionable_views(child_view):
                    temp_views.append(child_view)

            if len(temp_views) >= 1 and not meet_actionable_views:
                # continue the recursion if only one valid child view
                node_ptr = temp_views[0]
                node_ptr = self.__get_sole_child_view_2(node_ptr)
            return node_ptr

        else:
            # len(node_ptr['children']) == 0, node_ptr is the leaf node
            return node_ptr

    #
    def __get_tight_bound_child(self, view_tree_node):
        """
        get the tight bound of the view
        :param view_tree_node: the view tree node
        :return:
        """
        node_ptr = view_tree_node
        if len(node_ptr['children']) == 1:

            child_view = node_ptr['children'][0]

            # hot fix: if child_view is the view id
            if type(child_view) is int:
                child_view = self.views[child_view]

            if DeviceState.__is_non_actionable_wrapper(child_view):
                node_ptr = child_view
                node_ptr = self.__get_tight_bound_child(node_ptr)
                return node_ptr
            else:
                return node_ptr
        elif len(node_ptr['children']) > 1:
            return node_ptr
        else:  # len(node_ptr['children']) == 0, node_ptr is the leaf node
            return node_ptr

    #
    @staticmethod
    def __is_view_wrapper(view_tree_node):
        """
        check whether a view is of view wrapper: it should have at least one child
        :param view_tree_node: the given view
        :return:
        """
        if len(view_tree_node['children']) > 0:
            return True
        else:
            return False

    #
    @staticmethod
    def __is_non_actionable_wrapper(view_tree_node):
        """
        check whether a view is of non-actionable view wrapper: it should have at least one child but it is
            not actionable
        :param view_tree_node: the given view
        :return:
        """
        if DeviceState.__is_view_wrapper(view_tree_node) and (not DeviceState.__is_actionable_view(view_tree_node)):
            return True
        else:
            return False

    @staticmethod
    def __is_actionable_view_wrapper(view_tree_node):
        """
        check whether a view is of actionable view wrapper: it should have at least one child and it is an actionable
        view
        For an actionable view wrapper, we assume all its actionable child views depend on it/affect it
        :param view_tree_node: the given view
        :return:
        """
        if DeviceState.__is_view_wrapper(view_tree_node) and DeviceState.__is_actionable_view(view_tree_node):
            return True
        else:
            return False

    @staticmethod
    def __is_actionable_view(view_tree_node):
        """
        check whether the view is actionable (i.e., "clickable", "long_clickable", "editable", "checkable",
            and "scrollable" are true).
        :param view_tree_node: the given view
        :return: True, the view is actionable; False, otherwise
        """
        if view_tree_node['clickable'] or view_tree_node['long_clickable']:
            return True
        elif view_tree_node['editable']:
            return True
        elif view_tree_node['checkable']:
            return True
        elif view_tree_node['scrollable']:
            return True
        else:
            return False

    @staticmethod
    def __is_visible_view(view_tree_node):
        """
        check whether the view is visible or not
        :param view_tree_node:
        :return: True, if visible; False, otherwise
        """
        if view_tree_node['visible']:
            return True
        else:
            return False

    @staticmethod
    def is_leaf_view(view_tree_node):
        if len(view_tree_node['children']) == 0:
            return True
        else:
            return False

    @staticmethod
    def __contain_actionable_views(view_tree_node):
        """
        check whether the view and all its child views are non-actionable
        :param view_tree_node: the view tree node
        :return: True, if at least one view is actionable; False, if the view and all its child views are all
            non-actionable
        """
        if DeviceState.__is_actionable_view(view_tree_node):
            return True

        if DeviceState.is_leaf_view(view_tree_node) and (not DeviceState.__is_actionable_view(view_tree_node)):
            return False

        child_views = view_tree_node['children']
        for child in child_views:
            if DeviceState.__contain_actionable_views(child):
                return True
        return False

    #
    @staticmethod
    def __is_view_group_type(view_tree_node):
        """
        check whether the view is of a view group type
        the heuristic strategy to decide whether the view is of a view group type:
            1. the class of the view belongs to VIEW_GROUP_TYPE
        :param view_tree_node:
        :return: True, if it is of view group type; False, otherwise
        """
        class_name = view_tree_node['class']
        # we assume the children of these views satisfy the independent property
        view_group_type = [".view.ViewGroup", ".widget.RadioGroup",
                           ".widget.RelativeLayout", ".widget.LinearLayout", ".widget.FrameLayout",
                           ".widget.GridLayout",
                           ".widget.RecyclerView", ".widget.ListView", ".widget.GridView"
                           ]
        for view_type in view_group_type:
            if view_type in class_name:
                return True
        return False

    #
    @staticmethod
    def __check_actionable_type(view_list):
        """
        check whether all the views in the list are actionable or not
        :param view_list: the list of views
        :return: "NONE", none of them are actionable; "PARTIAL", some of them are actionable; "ALL", all of them
                are actionable
        """
        if len(view_list) <= 1:
            return "NONE"
        tmp_list = []
        for view in view_list:
            if DeviceState.__is_actionable_view(view):
                tmp_list.append("actionable")
            else:
                tmp_list.append("not_actionable")
        tmp_set = set(tmp_list)
        if len(tmp_set) == 2:
            return "PARTIAL"
        else:  # len(tmp_set) == 1
            if tmp_list[0] == "actionable":
                return "ALL"
            else:
                return "NONE"

    def annotate_view_with_color(self, image, view_dict: Dict, color: Tuple):
        """
        annotate a given view on its screenshot image
        :param image:
        :param view_dict
        :param color
        :return:
        """
        tight_child = self.__get_tight_bound_child(view_dict)
        tight_child_bounds = tight_child['bounds']
        cv2.rectangle(image, tuple(tight_child_bounds[0]), tuple(tight_child_bounds[1]), color, 2)

    def annotate_view_on_screenshot(self, original_screenshot_path, new_screenshot_path,
                                    view_list: List[Dict], color: Tuple):
        """
        annotate a given view on its screenshot
        :param original_screenshot_path: the original screenshot path
        :param new_screenshot_path: the new screenshot path
        :param view_list: the list of views to draw
        :param color: the color to draw
        :return:
        """
        image = cv2.imread(original_screenshot_path)
        for view_dict in view_list:
            tight_child = self.__get_tight_bound_child(view_dict)
            tight_child_bounds = tight_child['bounds']
            cv2.rectangle(image, tuple(tight_child_bounds[0]), tuple(tight_child_bounds[1]), color, 2)
        cv2.imwrite(new_screenshot_path, image)

    #
    def identify_independent_views(self, view_tree_nodes):
        """
        Identify independent views from a list of given views. This list of given views are the children views of
            their parent view.

        In our context, independent views should satisfy:
            (1) the views are the children of a parent view of some collection type (e.g., RecyclerView)
                This is the precondition when calling this function.
            (2) the views are actionable
                (if the view itself is not actionable but it has only one actionable child view, then also valid)
            (3) the views are of same type
                (the views have the same class type are more likely to serve independent, symmetric functionality)
        :param view_tree_nodes:
        :return:
        """

        # data structure:
        #   {'view_class_a': #view_class_a, 'view_class_b': #view_class_b, ...}
        view_types_dict: Dict[str, List[Dict]] = {}

        for view in view_tree_nodes:

            if DeviceState.__is_actionable_view(view):
                # the view itself is actionable

                view_class_name = view['class']
                if view_class_name in view_types_dict:
                    view_types_dict[view_class_name].append(view)
                else:
                    view_types_dict[view_class_name] = [view]

            elif DeviceState.__is_non_actionable_wrapper(view):
                child_view = self.__lift_child_view(view)
                if child_view is not None and DeviceState.__is_actionable_view(child_view):
                    # the view itself is a non-actionable view wrapper but it has only one actionable child view

                    view_class_name = child_view['class']
                    if view_class_name in view_types_dict:
                        view_types_dict[view_class_name].append(child_view)
                    else:
                        view_types_dict[view_class_name] = [child_view]
                else:
                    continue
            else:
                continue

        # get the ids of these independent views
        independent_views = []
        independent_view_ids = []

        if len(view_types_dict) > 0:

            # find the view type with the most number of views (we assume they are independent views)
            sorted_views_list: List[Tuple[str, List[Dict]]] = \
                sorted(view_types_dict.items(), key=lambda x: len(x[1]), reverse=True)
            views_with_max_number = sorted_views_list[0][1]

            for view_dict in views_with_max_number:
                independent_views.append(view_dict)
                independent_view_ids.append(view_dict['temp_id'])

        return independent_views, independent_view_ids

    #
    def __identify_independent_child_views_from_recyclerview(self, recycler_view, image=None, debug=False):
        """
        Identify independent child views from RecyclerView.
        We observe: (1) the next-level child views are usually (actionable) view wrappers rather than leaf views
                    (2) the next-level child views usually belong to the same type (in some rare cases, not all
                    next-level child views have the exactly same type, but most of them will)
        For all the next-level child views of RecyclerView (with the same type):
            If they are actionable, then they satisfy the independent property, and all the actionable child views of
                themselves depend on (or affect) themselves;
            If they are not actionable, then they are independent regions, and the action from one of these regions is
                independent from another region
        :param recycler_view: the RecylerView under check
        :return:
        """

        child_views = recycler_view['children']
        if len(child_views) == 0:
            return

        # get the independent child views
        independent_child_views, independent_child_view_ids = self.identify_independent_views(child_views)

        if len(independent_child_view_ids) >= 2:
            # Only for a view whose has >=2 independent child views, we will create 'independent_child_region_ids'

            actionable_flag = DeviceState.__check_actionable_type(independent_child_views)
            # if actionable_flag == "ALL":
            #     self.logger.info("All child views in RecyclerView/ListView/GridView are actionable.")
            # elif actionable_flag == "NONE":
            #     self.logger.info("All child views in RecyclerView/ListView/GridView are non-actionable.")
            # else:
            #     self.logger.info("Not all child views in RecyclerView/ListView/GridView are actionable.")

            # all child views are either actionable or non-actionable
            recycler_view['independent_child_region_ids'] = independent_child_view_ids

            # record the information on self.views
            recycler_view_id = recycler_view['temp_id']
            self.views[recycler_view_id]['independent_child_region_ids'] = independent_child_view_ids

            if debug:
                # debugging: annotate the independent child views and their parent
                self.annotate_view_with_color(image, self.views[recycler_view_id], COLOR_RED_TUPLE)
                for child_id in independent_child_view_ids:
                    self.annotate_view_with_color(image, self.views[child_id], COLOR_BLUE_TUPLE)

        else:
            # do nothing if no or only one view
            pass

    #
    def __identify_independent_child_views_from_listview(self, list_view, image=None, debug=False):
        """
        We observe that ListView is similar with RecyclerView
        :param list_view: the ListView under check
        :return:
        """
        self.__identify_independent_child_views_from_recyclerview(list_view, image, debug)

    #
    def __identify_independent_child_views_from_gridview(self, grid_view, image=None, debug=False):
        """
        We observe that GridView is similar with RecyclerView
        :param grid_view: the GridView under check
        :return:
        """
        self.__identify_independent_child_views_from_recyclerview(grid_view, image, debug)

    #
    def __lift_child_view(self, view_tree_node):
        """
        Lift the child view
        We observe: If a leaf view is wrapper by a single parent (an non-actionable view wrapper), then this leaf view
            can be safely lift to the level of its parent (we can image the leaf view substitute its parent).
            This lifting can be continued only if it is the single child of its parent (i.e., it does not have siblings
            before the lifting happens).
        :param view_tree_node: the parent view node
        :return: None, if the given parent view node does not satisfy this observation; View, the lifted leaf view
        """
        child_view = self.__get_sole_child_view(view_tree_node)
        if DeviceState.is_leaf_view(child_view):
            return child_view
        else:
            return None

    #
    def __identify_independent_child_views_from_layout(self, layout_view, image=None, debug=False):
        """
        Identify independent child views of LinearLayout and RelativeLayout
        The heuristic strategy:
            We assume all the next-level child views satisfy the independent property.
        We observe:
            (1) the next-level child views can have different view types
            (2) the next-level child views can be leaf views or wrapper views
        :param layout_view:
        :return:
        """
        child_views = layout_view['children']
        if len(child_views) == 0:
            return

        # get the independent child views
        independent_child_views, independent_child_view_ids = self.identify_independent_views(child_views)

        if len(independent_child_views) >= 2:
            layout_view['independent_child_region_ids'] = independent_child_view_ids
            # record the information on self.views
            layout_view_id = layout_view['temp_id']
            self.views[layout_view_id]['independent_child_region_ids'] = independent_child_view_ids

            if debug:
                # Only for debugging: annotate the independent child views and their parent
                layout_view_bounds = layout_view['bounds']
                cv2.rectangle(image, tuple(layout_view_bounds[0]), tuple(layout_view_bounds[1]), (0, 0, 255), 2)
                for child_id in independent_child_view_ids:
                    tight_child = self.__get_tight_bound_child(self.views[child_id])
                    tight_child_bounds = tight_child['bounds']
                    cv2.rectangle(image, tuple(tight_child_bounds[0]), tuple(tight_child_bounds[1]), (255, 0, 0), 2)
        else:
            # do nothing if only one child view exists or no child views exist
            pass

    #
    def __identify_independent_child_views_from_view_group(self, view_group, image=None, debug=False):
        """
        We observe: ViewGroup (RadioGroup) has similar behaviors with LinearLayout or RelativeLayout
        :param view_group:
        :return:
        """
        self.__identify_independent_child_views_from_layout(view_group, image, debug)

    #
    def __identify_independent_child_views(self, view_group, image=None, debug=False):
        """
        get the next-level child views (which satisfy the independent property) from a view with view-group type
        the heuristic strategy to get the next-level child views (satisfying the independent property):
            1. the valid child views usually have the same view type (although we cannot guarantee these views
            must have symmetric structure)
            2. the child views account for the majority (in rare cases, some of these child views may have different
            view types with others)
            3. the independent property is for *actionable* views
        :param view_group: the view of view group type
        :return:
        """

        # "RecyclerView", "ListView", and "GridView" are similar
        if ".widget.RecyclerView" in view_group['class']:
            self.__identify_independent_child_views_from_recyclerview(view_group, image, debug)
        elif ".widget.ListView" in view_group['class']:
            self.__identify_independent_child_views_from_listview(view_group, image, debug)
        elif ".widget.GridView" in view_group['class']:
            self.__identify_independent_child_views_from_gridview(view_group, image, debug)

        # Including the cases ".widget.LinearLayout", ".widget.LinearLayoutCompat"
        elif ".widget.RelativeLayout" in view_group['class'] or ".widget.LinearLayout" in view_group['class'] or \
                ".widget.FrameLayout" in view_group['class'] or ".widget.GridLayout" in view_group['class']:
            self.__identify_independent_child_views_from_layout(view_group, image, debug)

        elif ".view.ViewGroup" in view_group['class'] or ".widget.RadioGroup" in view_group['class']:
            # We observe: RadioGroup is a special ViewGroup where each child views are actionable leaf views
            self.__identify_independent_child_views_from_view_group(view_group, image, debug)

    # get the independent views
    def get_all_independent_views(self):
        """
        Get the ids of all independent views (i.e., the views we can select from a given device state).
        These independent views will be added into independent traces.
        :return: Set(int)
        """
        all_selectable_views_set: Set[int] = set()
        active_views_set = set()  # the active views which will be excluded from selectable views

        for view_dict in self.views:
            if DeviceState.__is_actionable_view(view_dict):
                all_selectable_views_set.add(view_dict['temp_id'])
            if 'active_view' in view_dict:
                active_views_set = active_views_set | set(view_dict['active_view'])

        independent_views_set = all_selectable_views_set - active_views_set

        # self.logger.info("------")
        # self.logger.info("the independent views:")
        # for i in independent_views_set:
        #     self.logger.info("view id: %d, %s" % (self.views[i]['temp_id'],
        #                                           DeviceState.__get_view_signature(self.views[i])))
        # self.logger.info("------")

        return independent_views_set

    def __get_all_actionable_child_views(self, view_dict):
        """
        get all actionable child views of a given view
        :param view_dict: the given view
        :return: Set, the set of actionable child views
        """

        children = self.__safe_dict_get(view_dict, 'children')
        if not children:
            return set()

        actionable_children = set()
        for child in children:
            if DeviceState.__is_actionable_view(child):
                actionable_children.add(child)

        # print("--children before loop")
        # print(children)
        for child in actionable_children:
            # print("child id: %d" % child)

            children_of_child = self.get_all_children(self.views[child])

            # print("children of this child: ")
            # print(children_of_child)
            actionable_children = actionable_children.union(children_of_child)

        # print("--return total children:")
        # print(children)
        return actionable_children

    def __get_parent_view_of_independent_region(self, view_dict):
        """
        :param view_dict: the view dict
        :return: dict, the parent view of the independent region
        """
        current_view = view_dict
        while True:
            parent_id = self.__safe_dict_get(current_view, 'parent', -1)
            if 0 <= parent_id < len(self.views):
                parent_view_dict = self.views[parent_id]
                current_view = parent_view_dict
                if 'independent_child_region_ids' in parent_view_dict:
                    break
            else:
                # exit the loop if parent_id == -1 !!!
                break

        if parent_id == -1:
            # Return None if the view does not have independent child views
            return None

        return current_view

    # parse the view tree to infer independent property
    def __parse_view_tree(self, root_view, screenshot_path, debug=False):
        """
        Use a breadth-first search to parse the view tree
        :param root_view: the view tree obtained from "__parse_views"
        :param screenshot_path: the screenshot of the view tree
        :return:
        """

        # load the screenshot
        image = cv2.imread(screenshot_path) if debug else None

        view_queue = queue.Queue()
        view_queue.put(root_view)

        while view_queue.qsize() != 0:

            view_tree_node_ptr = view_queue.get()  # view_tree_node_ptr points to the current view node
            view_tree_node_ptr = self.__get_sole_child_view(view_tree_node_ptr)

            # If the node is a non-actionable view wrapper but it has more than one child
            if DeviceState.__is_view_wrapper(view_tree_node_ptr):

                # add the child views into the queue
                child_views = view_tree_node_ptr['children']
                for child in child_views:
                    if DeviceState.__is_visible_view(child) and DeviceState.__contain_actionable_views(child):
                        view_queue.put(child)

                # If the node is of view group type
                if DeviceState.__is_view_group_type(view_tree_node_ptr):  # if it is of view group type
                    # identify independent child views
                    self.__identify_independent_child_views(view_tree_node_ptr, image, debug)

                # If the node is an actionable view wrapper
                if self.__is_actionable_view_wrapper(view_tree_node_ptr):
                    # TODO need to give a good name for the key 'group', here we may need to record “view_tree_node_ptr"
                    # should be the head of a group of views
                    view_tree_node_ptr['group'] = True

            # if the node is a leaf (it could be actionable or not)
            elif DeviceState.is_leaf_view(view_tree_node_ptr):
                # do nothing
                pass
            else:
                pass

        if debug:
            # dump the annotated screenshot
            cv2.imwrite(screenshot_path.replace(".png", "_annotated.png"), image)

    #################

    def find_matched_view(self, view_to_match):
        matched_view = None
        for view_dict in self.views:
            if 'class' in view_to_match and not safe_re_match(re.compile(view_to_match['class']), view_dict['class']):
                continue
            if 'resource_id' in view_to_match and not safe_re_match(re.compile(view_to_match['resource_id']),
                                                                    view_dict['resource_id']):
                continue
            if 'text' in view_to_match and not safe_re_match(re.compile(view_to_match['text']), view_dict['text']):
                continue
            matched_view = view_dict
            break
        return matched_view

    @staticmethod
    def are_views_match(view_dict_1, view_dict_2):
        if 'class' in view_dict_1 and 'class' in view_dict_2 and \
                not safe_re_match(re.compile(view_dict_1['class']), view_dict_2['class']):
            return False
        if 'resource_id' in view_dict_1 and 'resource_id' in view_dict_2 and \
                not safe_re_match(re.compile(view_dict_1['resource_id']), view_dict_2['resource_id']):
            return False
        if 'text' in view_dict_1 and 'text' in view_dict_2 and \
                not safe_re_match(re.compile(view_dict_1['text']), view_dict_2['text']):
            return False
        if 'content_description' in view_dict_1 and 'content_description' in view_dict_2 and \
                not safe_re_match(re.compile(view_dict_1['content_description']), view_dict_2['content_description']):
            return False

        return True

    @staticmethod
    def are_views_equal(view_dict_1, view_dict_2):
        if 'class' in view_dict_1 and 'class' in view_dict_2 and \
                not (view_dict_1['class'] == view_dict_2['class']):
            return False
        if 'resource_id' in view_dict_1 and 'resource_id' in view_dict_2 and \
                not (view_dict_1['resource_id'] == view_dict_2['resource_id']):
            return False
        if 'text' in view_dict_1 and 'text' in view_dict_2 and \
                not (view_dict_1['text'] == view_dict_2['text']):
            return False
        if 'content_description' in view_dict_1 and 'content_description' in view_dict_2 and \
                not (view_dict_1['content_description'] == view_dict_2['content_description']):
            return False

        if 'selected' in view_dict_1 and 'selected' in view_dict_2 and \
                not (view_dict_1['selected'] == view_dict_2['selected']):
            return False

        return True

    #
    def annotate_active_view(self, view_dict):
        """
        Annotate the given view_dict as ACTIVE if this view belongs to a set of independent views of a parent view.

        In practice, we use the field 'active_view' of the parent view to denote which independent child view now is
            active.

        Note that we annotate active view only when the parent view has independent child views.
        :param view_dict:
        :return:
        """
        parent_view = self.__get_parent_view_of_independent_region(view_dict)
        if parent_view is None:
            # Return if the parent view does not have independent child views
            #   In this case, we do not need to annotate 'active_view'.
            return
        if view_dict['temp_id'] in parent_view['independent_child_region_ids']:
            # check whether view_dict belongs to the set of independent views of a parent view
            parent_view['active_view'] = [view_dict['temp_id']]
            self.logger.info("annotated active view: \n the child view (id: %d, %s) "
                             "\n\t is annotated in \n its parent view (id: %d, %s)" %
                             (view_dict['temp_id'], DeviceState.__get_view_signature(view_dict),
                              parent_view['temp_id'], DeviceState.__get_view_signature(parent_view)))
        else:
            self.logger.info("this view does not belong to a set of independent views, so we do not annotate it.")

    @staticmethod
    def get_view_text_sensitive_signature(view_dict, include_view_text=True):
        """
        Get the text sensitive signature of the given view for computing tree edit distance.
        Specifically, we focus on using the three elements "class", "resource_id", "content_description", "text"
        (without considering actionable properties). This is one abstraction strategy for a view.

        @param view_dict: the view dict
        @param include_view_text: whether to include text
        @return: str
        """
        if 'text-sensitive-signature' in view_dict:
            return view_dict['text-sensitive-signature']

        view_text = DeviceState.__safe_dict_get(view_dict, 'text', "None")
        if view_text is None or len(view_text) > 50 or include_view_text is False:
            view_text = "None"

        if DeviceState.include_content_desc:

            signature = "[class]%s[resource_id]%s[content_desc]%s[text]%s" % \
                        (DeviceState.__safe_dict_get(view_dict, 'class', "None"),
                         DeviceState.__safe_dict_get(view_dict, 'resource_id', "None"),
                         DeviceState.__safe_dict_get(view_dict, 'content_description', "None"),
                         view_text)
        else:
            signature = "[class]%s[resource_id]%s[text]%s" % \
                        (DeviceState.__safe_dict_get(view_dict, 'class', "None"),
                         DeviceState.__safe_dict_get(view_dict, 'resource_id', "None"),
                         view_text)

        view_dict['text-sensitive-signature'] = signature

        return signature

    @staticmethod
    def is_view_different(current_view, another_view):
        """
        Compare whether the current view is different from another view in terms of their text sensitive signatures
        :return:
        """
        current_view_signature = DeviceState.get_view_text_sensitive_signature(current_view)
        another_view_signature = DeviceState.get_view_text_sensitive_signature(another_view)
        if current_view_signature != another_view_signature:
            return True
        else:
            return False

    def get_view_content_sensitive_str(self, view_dict, include_children=True, include_text=True):
        """
        get a string which can represent the given view, including the view itself and its all children
        :param view_dict: dict, an element of DeviceState.views
        :param include_children: boolean, whether to include all the children of the given view
        :param include_text: boolean, whether to include the text
        :return:
        """
        if include_text:
            view_signature = DeviceState.get_view_text_sensitive_signature(view_dict)
        else:
            view_signature = DeviceState.__get_content_free_view_signature(view_dict)

        if include_children:
            child_strs = []
            # We consider the view self and its all children
            for child_id in self.get_all_children(view_dict):

                if child_id > len(self.views):
                    # Hot fix: list index out of range
                    continue

                child_view = self.views[child_id]

                if child_view['is_ignored']:
                    # exclude the child view if it is ignored
                    continue

                if include_text:
                    child_strs.append(DeviceState.get_view_text_sensitive_signature(child_view))
                else:
                    child_strs.append(DeviceState.__get_content_free_view_signature(child_view))

            child_strs.sort()

            view_str = "Self:%s\nChildren:%s" % (view_signature, "||".join(child_strs))

        else:
            view_str = "Self:%s" % view_signature

        return view_str

    # def compute_view_trace_signature(self, view_dict, include_children=True, exclude_text=False, ignore_views=None):
    #     """
    #     Compute the trace signature of view dict in the current state.
    #     In principle, the trace signature
    #
    #     Algorithm:
    #         1. compute the trace from the root node until the given view dict, e.g., [n1, n2, view_dict, n3, n4]
    #             Here, n1 and n2 are parent views, n3 and n4 are child views.
    #         2. collect the structure (i.e., content-free) info (class, resource id) of parent views,
    #             and the content-sensitive info (class, resource id, and view text) of the view dict and all its
    #             children.
    #     :param view_dict: the given view
    #     :param include_children: Boolean, whether to include all the children of the given view
    #     :param exclude_text: Boolean, whether to exclude texts
    #     :param ignore_views: the views that should be ignored when computing view trace signature
    #     :return: str
    #     """
    #
    #     # if 'coarse-view-trace-signature' in view_dict:
    #     #     return view_dict['coarse-view-trace-signature']
    #
    #     # get the content free signature of view_dict's parent and all its ancestors
    #     view_trace = self.get_all_ancestors(view_dict)
    #     view_trace.reverse()
    #
    #     view_signatures = []
    #     for view_id in view_trace:
    #         view = self.views[view_id]
    #         view_signature = DeviceState.__get_content_free_view_signature(view)
    #         if view_signature:
    #             view_signatures.append(view_signature)
    #     view_trace_signature = "%s" % (",".join(view_signatures))
    #
    #     # get the content sensitive signature of view_dict and all its children
    #     view_dict_content_sensitive_signature = self.get_view_content_sensitive_str(view_dict,
    #                                                                                 include_children=include_children,
    #                                                                                 include_text=exclude_text)
    #
    #     view_trace_signature = view_trace_signature + view_dict_content_sensitive_signature
    #
    #     # view_dict['coarse-view-trace-signature'] = view_trace_signature
    #     return view_trace_signature

    #
    def get_ancestor_view_by_tree_level(self, current_view_dict, backtrack_tree_level=0):
        """
        Get the ancestor of the given view by backtracking the view tree until this ancestor has more than one children,
        i.e., until we have included some proper ``sibling`` views of the given view.
        These siblings are used to represent the context of the given view.

        Specifically, during the backtrack, we actually skip over the ancestor view if it has only one valid (not-ignored)
        child view. The effect is that we lift the given view upward until we find a set of proper ``sibling`` views.

        :param current_view_dict: the given current view dict
        :param backtrack_tree_level: how many tree levels we backtrack.
                            By default, we assume backtracking one tree level will be enough.
        :return: dict, the target ancestor view
        """
        # this overwrites the value of ``backtrack_tree_level``
        # backtrack_tree_level = self.view_context_str_backtrack_level

        target_ancestor_view = current_view_dict

        while True:

            if backtrack_tree_level == 0:
                break

            ancestor_view_id = self.__safe_dict_get(target_ancestor_view, 'parent', -1)
            if 0 <= ancestor_view_id < len(self.views):
                target_ancestor_view = self.views[ancestor_view_id]

                # TODO we comment this because we will handle false positives offline
                # A valid child view satisfies: child_view['is_ignored'] == False
                # valid_child_views_cnt = 0
                # children = target_ancestor_view['children']
                # for child in children:
                #     child_view = self.views[child]
                #     if not child_view['is_ignored']:
                #         valid_child_views_cnt += 1

                children = target_ancestor_view['children']

                if len(children) > 1:
                    # subtract one tree level if the target ancestor view has more than one valid children view
                    backtrack_tree_level -= 1

            if ancestor_view_id == -1:
                # break the loop if we reach the top view
                break

        return target_ancestor_view

    #
    def locate_matched_views(self, target_view_dict, another_state: 'DeviceState', ignored_views=None):
        """
        Find the views of the current state that are matched with a given view dict from another state.
        The views are sorted in the weight of similarity from the most to the least.

        The algorithm:

            Scan the views of the current state to check whether there exists some views that are similar to the target
            view.

            Due to some compound views (i.e., the views that have children views) may change, e.g., its own text
            may change, its children views' texts may change, new children views may be added, original children
            views may be deleted, we design two strategies to locate the matched view.

            The main goal of adding approximate mode is to improve the executable rate of mutant tests, although
            sacrificing the precision.

            1. [Precise Mode]
            use the given view dict's context sensitive properties (i.e., class, resource-id, text,
                and these three properties of children views) to locate whether any matched views that exist
                in the current state.

            2. [Approximate Mode]
            only use the given view dict's context insensitive properties (i.e., class, resource-id,
                and its actionable properties, do not consider any properties of its children views) to locate whether
                any matched views that exist in the current state.

            Next,

            Let the candidate views in the current (computed from the above step) state be candidate_views.
            We use the context info of view_dict to locate which candidate in candidate_views is most matched.

            Specifically,

                2. get the context string of view_dict and those of views in the candidate_views

                3. use the string difference ratio to sort the similarity of these candidate views

                Optimization implementation:

                (1) https://pypi.org/project/python-Levenshtein/
                (2) https://stackoverflow.com/questions/6690739/high-performance-fuzzy-string-comparison-in-python-use-levenshtein-or-difflib

        :param target_view_dict: the target view dict (from another state) that we aim to locate in the current state
        :param another_state:   the another state where the target view dict in
        :param ignored_views:
        :return: (list, bool)
        """

        print("\n****Begin to locate matched views ...***")
        target_view_str = another_state.get_view_content_sensitive_str(target_view_dict)
        print("\nThe target view: %s \n its view_str: %s \n" % (target_view_str, target_view_dict['view_str']))
        ancestor_view = another_state.get_ancestor_view_by_tree_level(target_view_dict)
        views_with_children_order_ignored = \
            ignored_views.get_views_with_children_order_ignored(another_state.foreground_activity) \
                if ignored_views is not None else None
        target_view_context_string = \
            another_state.get_view_context_string(ancestor_view,
                                                  view_dicts_with_children_order_ignored=views_with_children_order_ignored)

        # If a candidate view has the exact same context sensitive str, then it will be recorded in this list
        tmp_matched_views_with_same_view_content_sensitive_str = []
        # However, the above criterion is very strict. In some cases, the children views may change. In those
        #   cases, the context sensitive strs are different.
        # To relax the above strict criterion, we assume if a candidate view has the same properties, then it will
        #   also be recorded but annotated with approximate precision.
        tmp_matched_views_with_same_view_properties = []

        views_with_children_order_ignored = \
            ignored_views.get_views_with_children_order_ignored(self.foreground_activity) \
                if ignored_views is not None else None

        # scan the current state to collect matched views
        for view_dict in self.views:
            if not DeviceState.__is_actionable_view(view_dict):
                # TODO not very sure about this condition, maybe too strict??
                #  But it safely skips the view if it is not actionable
                #  (only actionable views could be a matched candidate)
                continue

            view_str = self.get_view_content_sensitive_str(view_dict)
            if view_str == target_view_str:
                print("**exact matched view**, view temp id: %s, "
                      "view_content_sensitive_str: %s" % (view_dict['temp_id'], view_str))

                # record the view if their view trace signatures are similar
                ancestor_view = self.get_ancestor_view_by_tree_level(view_dict)
                view_dict_context_string = \
                    self.get_view_context_string(ancestor_view,
                                                 view_dicts_with_children_order_ignored=views_with_children_order_ignored)
                tmp_matched_views_with_same_view_content_sensitive_str.append((view_dict, view_dict_context_string))
            else:
                if DeviceState.get_view_property_values(view_dict) == DeviceState.get_view_property_values(
                        target_view_dict):
                    print("**approximate matched view**, view temp id: %s, "
                          "view_content_sensitive_str: %s" % (view_dict['temp_id'], view_str))

                    # record the view if their view trace signatures are similar
                    ancestor_view = self.get_ancestor_view_by_tree_level(view_dict)
                    view_dict_context_string = \
                        self.get_view_context_string(ancestor_view,
                                                     view_dicts_with_children_order_ignored=views_with_children_order_ignored)

                    tmp_matched_views_with_same_view_properties.append((view_dict, view_dict_context_string))

        print("\nfind %d exact matched views (when consider the view itself and its children views)\n"
              "find %d approximate matched views (when consider the view itself)\n\n" %
              (len(tmp_matched_views_with_same_view_content_sensitive_str),
               len(tmp_matched_views_with_same_view_properties)))

        if len(tmp_matched_views_with_same_view_content_sensitive_str) != 0:
            exact_matched_view_tuple, tmp_total_matched_views_with_matchness, \
            tmp_approximate_matched_views_with_matchness, found_exactly_matched_view = \
                DeviceState.__sort_view_similarity(target_view_dict, target_view_context_string,
                                                   tmp_matched_views_with_same_view_content_sensitive_str)
        else:
            exact_matched_view_tuple, tmp_total_matched_views_with_matchness, \
            tmp_approximate_matched_views_with_matchness, found_exactly_matched_view = \
                DeviceState.__sort_view_similarity(target_view_dict, target_view_context_string,
                                                   tmp_matched_views_with_same_view_properties)

        # the final result of matched views ranked by the matchness
        final_matched_views_with_matchness = []
        if exact_matched_view_tuple is not None:
            final_matched_views_with_matchness.append(exact_matched_view_tuple)
        final_matched_views_with_matchness.extend(tmp_total_matched_views_with_matchness)

        # sort the views with the string similarity from most similar to least similar
        final_matched_views_with_matchness.extend(
            sorted(tmp_approximate_matched_views_with_matchness, key=lambda x: x[0], reverse=True))

        matched_views = []
        for (_, view_dict, _) in final_matched_views_with_matchness:
            matched_views.append(view_dict)

        print("****End locate matched views ...***\n\n")

        return matched_views, found_exactly_matched_view

    @staticmethod
    def __sort_view_similarity(target_view_dict, target_view_context_string, candidate_views):

        print("*** Sort the similarity ****")

        # the flag that indicates whether we found an exactly matched view
        found_exactly_matched_view = False

        tmp_approximate_matched_views_with_similarity = []
        tmp_total_matched_views_with_similarity = []  # total
        exact_matched_view_tuple = None  # exactly matched view (with same context string and view id)

        print("check the candidate views...")
        print("target view's context str: %s\n", target_view_context_string)
        for (view_dict, view_dict_context_string) in candidate_views:
            similarity_ratio = Levenshtein.ratio(target_view_context_string, view_dict_context_string)
            print("candidate view's context str: %s", view_dict_context_string)
            if similarity_ratio == 1.0:
                if view_dict['sibling_id'] == target_view_dict['sibling_id'] and (not found_exactly_matched_view):
                    # handle special cases when context string lose effect
                    #   (i.e., multiple views have exact same context string)
                    print("\nfind one view is exactly matched!!")
                    exact_matched_view_tuple = (similarity_ratio, view_dict, view_dict_context_string)
                    found_exactly_matched_view = True  # make sure we matched with only one view
                    # print("exactly matched: %s" % str(view_dict['bounds']))
                else:
                    tmp_total_matched_views_with_similarity.append(
                        (similarity_ratio, view_dict, view_dict_context_string))
                    # print("exactly matched (not the first one): %s" % str(view_dict['bounds']))
            else:
                print("\nfind one view is approximately matched!!")
                tmp_approximate_matched_views_with_similarity.append(
                    (similarity_ratio, view_dict, view_dict_context_string))
                # print("approximately matched: %s" % str(view_dict['bounds']))

        return exact_matched_view_tuple, tmp_total_matched_views_with_similarity, \
               tmp_approximate_matched_views_with_similarity, found_exactly_matched_view

    #
    def update_active_views_from_prev_comparable_state(self, prev_state):
        """
        update the active views from one previous, comparable state to the current state
        :param prev_state: the previous state
        :return:
        """
        # Get all active views of another state
        active_views_of_prev_state = []
        for view_dict in prev_state.views:
            if 'active_view' in view_dict:
                # view_dict['active_view'] is a list that contains only one element (i.e., the current active view's id)
                active_view_id = view_dict['active_view'][0]
                active_views_of_prev_state.append(prev_state.views[active_view_id])

        # For each active view, find the corresponding matchable views from the current state
        for active_view in active_views_of_prev_state:

            matched_active_views_of_current_state, found_exact_match = self.locate_matched_views(active_view,
                                                                                                 prev_state)
            if len(matched_active_views_of_current_state) == 0 or not found_exact_match:
                # skip if no matched views or no exact matched views (reduce false positives) were found
                continue
            else:
                # at least one view is matched, get the first element (with the most matchness)
                most_matched_view_of_current_state = matched_active_views_of_current_state[0]
                self.annotate_active_view(most_matched_view_of_current_state)
                # parent_view_dict = self.__get_parent_view_of_independent_region(most_matched_view_of_current_state)
                # parent_view_dict['active_view'] = [most_matched_view_of_current_state['temp_id']]

    @staticmethod
    def are_comparable_states(current_state: 'DeviceState', another_state: 'DeviceState', gui_page_types_info=None):
        """
        Check whether current_state and another_state are comparable.
        Ideally, only two GUI pages have the same activity (and window stack) can be compared.
        Here, we use a simple heuristic strategy:
            1. get the view trees of these two states
            2. If the two trees are different at the top-N level (N=1), then these two GUI pages are not comparable
               We only consider visible views, and by "different" we mean the class (not including resource-id and text)
        :param current_state:
        :param another_state:
        :param gui_page_types_info:
        :return: boolean
        """
        if current_state.foreground_activity != another_state.foreground_activity:
            # This condition covers:
            #   (1) one same app with two different activities
            #   (2) activities from two different apps
            return False

        else:
            # current_state.foreground_activity == another_state.foreground_activity:

            current_state_page_width = current_state.views[0]['bounds'][1][0]
            current_state_page_height = current_state.views[0]['bounds'][1][1]

            another_state_page_width = another_state.views[0]['bounds'][1][0]
            another_state_page_height = another_state.views[0]['bounds'][1][1]

            # TODO hardcode the screen size, need to modify if we change to different screen sizes
            # device_with = current_state.device.get_width() //800
            # device_height = current_state.device.get_height() //1280
            device_with = 800
            device_height = 1280

            if current_state_page_width < device_with and current_state_page_height < device_height and \
                    another_state_page_width == device_with and another_state_page_height == device_height:
                return False

            if another_state_page_width < device_with and another_state_page_height < device_height and \
                    current_state_page_width == device_with and current_state_page_height == device_height:
                # If one state is a full-screen page (should be an activity)
                #   and the other state is not full-screen page (should be a window),
                # then these two pages must be different
                return False

            if current_state.__drawer_view_is_opened != another_state.__drawer_view_is_opened:
                # Fix issue #24
                #   This condition covers the comparison between the main activity view and its drawer view.
                #   These two views have the same length of window stack with the same activity name.
                return False

            res = DeviceState.fine_grained_state_similarity_checking(current_state, another_state, gui_page_types_info)

            return res

    @staticmethod
    def fine_grained_state_similarity_checking(current_state: 'DeviceState', another_state: 'DeviceState',
                                               gui_page_types_info=None):

        # This handles the remaining case:
        #   We use a very simple heuristic to differentiate them by comparing the first level of children views.
        children_views_of_current_state = \
            current_state.__get_sole_child_view_2(current_state.view_tree)['children']
        children_views_of_another_state = \
            another_state.__get_sole_child_view_2(another_state.view_tree)['children']

        if len(children_views_of_current_state) != len(children_views_of_another_state):
            # not comparable if the number of child views are not equal
            return False
        else:
            cnt = len(children_views_of_current_state)
            for i in range(0, cnt):
                child_view_of_current_state = children_views_of_current_state[i]
                child_view_of_another_state = children_views_of_another_state[i]
                if child_view_of_current_state['class'] != child_view_of_another_state['class']:
                    # not comparable if the classes are different
                    return False

            if gui_page_types_info is not None:
                # check gui page types if the info is given

                gui_page_type_1 = current_state.gui_page_type if current_state.gui_page_type is not None \
                    else current_state.get_gui_page_type(gui_page_types_info)
                gui_page_type_2 = another_state.gui_page_type if another_state.gui_page_type is not None \
                    else another_state.get_gui_page_type(gui_page_types_info)

                if gui_page_type_1 != gui_page_type_2:
                    return False

            return True

    def sort_children_views(self, view_dict):
        """
        Sort the children of given view dict by their content sensitive strs

        :param view_dict:
        :return:
        """

        children = self.__safe_dict_get(view_dict, 'children')
        if len(children) <= 0:
            return

        tmp_children_list: List[Tuple[str, int]] = []
        for child_id in children:
            child_content_str = self.get_view_content_sensitive_str(self.views[child_id])
            tmp_children_list.append((child_content_str, child_id))

        # sort the children views according to their content sensitive str
        tmp_sorted_children_list = sorted(tmp_children_list, key=lambda x: x[0])

        sorted_children: List[int] = []
        for (child_content_str, child_id) in tmp_sorted_children_list:
            sorted_children.append(child_id)
        self.__safe_dict_set(view_dict, 'children', sorted_children)

        return

    def get_view_context_string(self, view_dict, include_view_text=True, view_dicts_with_children_order_ignored=None):
        """
        Get the context string (i.e., the brace string internally maintained) of a view dict.

        :param view_dict: the given view dict
        :param include_view_text, whether to include text
        :param view_dicts_with_children_order_ignored
        :return: str
        """
        # fixed an issue: use view id to retrieve 'brace_string'
        view_dict_id = DeviceState.__safe_dict_get(view_dict, 'temp_id')
        target_view_dict = self.views[view_dict_id]

        if 'brace_string' in target_view_dict:
            return target_view_dict['brace_string']

        # compute the brace string for the whole tree
        self.tree_to_brace_string(self.views[0],
                                  include_view_text=include_view_text,
                                  view_dicts_with_children_order_ignored=view_dicts_with_children_order_ignored)

        if 'brace_string' not in target_view_dict:
            # print("Error: we failed to find the key \'brace_string\' when getting view context string")
            return ""

        return target_view_dict['brace_string']

    def tree_to_brace_string(self, view_dict, postorder_view_id=1, include_view_text=True,
                             view_dicts_with_children_order_ignored=None):
        """
        Use the post-order traversal to convert the view tree (rooted at ``view_dict``) of a device state into a
        brace-format string, and assign a post-order id for each view (i.e., the id is assigned in a post-order).
        The purpose is to use the tree edit distance algorithm.

        Specifically, we maintain the mapping between a view dict's postorder view id and its original view id in
        self.mapping_between_postorder_and_original_view_ids. This allows us to access the specific view dict in O(1)
        via its postorder view id. The original view id is assigned in the pre-order traversal format.

        Post-order traversal: https://www.geeksforgeeks.org/tree-traversals-inorder-preorder-and-postorder/

        brace-format string:
            The trees are encoded in the bracket notation, for example, in tree {A{B{X}{Y}{F}}{C}} the root node
            has label A and two children with labels B and C. B has three children with labels X, Y, F.

        # when we get the specific view, we compute its 1-level context, when comparing context by using sat
        #   compute the set difference, if empty, then the context is same, otherwise not same

        :param view_dict, the root view dict (on the view tree) where the computation starts.
        :param postorder_view_id, the post-order view id for view_dict
        :param include_view_text, whether to include view text
        :param view_dicts_with_children_order_ignored: ignore the order of this view's children
                (specially used for ignoring the order of children views)
        :return:
        """

        children = self.__safe_dict_get(view_dict, 'children')

        if len(children) == 0:
            # If the view dict is a leaf view

            temp_brace_string = "{" + self.get_view_text_sensitive_signature(view_dict,
                                                                             include_view_text=include_view_text) + "}"

            # assign the postorder view id
            view_dict['postorder_view_id'] = postorder_view_id

            # record the mapping relation between postorder view ids and original view ids
            self.mapping_between_postorder_and_original_view_ids.append(
                {view_dict['postorder_view_id']: view_dict['temp_id']})

            # record "brace_string" for each view
            view_dict['brace_string'] = temp_brace_string

            # Return
            return temp_brace_string, postorder_view_id

        # NOTE: we do not ignore the root view dict even if it is ignored!!
        temp_brace_string = "{" + self.get_view_text_sensitive_signature(view_dict, include_view_text=include_view_text)

        # # Ignore the order of this view's children views
        # children = self.sort_children_views_by_view_content_sensitive_str(view_dict,
        #                                                                   children,
        #                                                                   view_dicts_with_children_order_ignored)
        for child in children:
            # If the view dict is a non-leaf view

            child_of_view_dict = self.views[child]

            if child_of_view_dict['is_ignored']:
                # NOTE: if the view dict is not a leaf node but it is ignored, then the current implementation
                #   will ignore all its children views!!!
                # Also: we set its brace_string as empty to avoid KeyError
                child_of_view_dict['brace_string'] = ""
                continue

            child_brace_string, postorder_view_id = \
                self.tree_to_brace_string(child_of_view_dict, postorder_view_id=postorder_view_id,
                                          view_dicts_with_children_order_ignored=view_dicts_with_children_order_ignored)
            temp_brace_string += child_brace_string
            postorder_view_id += 1

        temp_brace_string += "}"

        # record "postorder_id" for each view
        view_dict['postorder_view_id'] = postorder_view_id
        # record the mapping relation between postorder view ids and original view ids
        self.mapping_between_postorder_and_original_view_ids.append(
            {view_dict['postorder_view_id']: view_dict['temp_id']})

        # record "brace_string" for each view
        view_dict['brace_string'] = temp_brace_string

        # Return
        return temp_brace_string, postorder_view_id

    def get_view_dict_by_postorder_view_id(self, postorder_view_id: int):
        """
        get the view dict by its postorder view id from the state
        :param postorder_view_id: the postorder view id
        :return: dict, the view dict
        """
        # get the mapping dict of view ids (i.e., the post-order view id with the original view id)
        mapping_dict_of_view_ids = self.mapping_between_postorder_and_original_view_ids[postorder_view_id]

        original_view_id = mapping_dict_of_view_ids[postorder_view_id]
        return self.views[original_view_id]

    #################

    def __generate_view_strs(self):
        for view_dict in self.views:
            self.__get_view_str(view_dict)
            # self.__get_view_structure(view_dict)

    @staticmethod
    def __calculate_depth(views):
        root_view = None
        for view in views:
            if DeviceState.__safe_dict_get(view, 'parent') == -1:
                root_view = view
                break
        DeviceState.__assign_depth(views, root_view, 0)

    @staticmethod
    def __assign_depth(views, view_dict, depth):
        view_dict['depth'] = depth
        for view_id in DeviceState.__safe_dict_get(view_dict, 'children', []):
            DeviceState.__assign_depth(views, views[view_id], depth + 1)

    def __get_state_str(self):
        state_str_raw = self.__get_state_str_raw()
        return md5(state_str_raw)

    def __get_state_str_raw(self):
        if self.device.humanoid is not None:
            import json
            from xmlrpc.client import ServerProxy
            proxy = ServerProxy("http://%s/" % self.device.humanoid)
            return proxy.render_view_tree(json.dumps({
                "view_tree": self.view_tree,
                "screen_res": [self.device.display_info["width"],
                               self.device.display_info["height"]]
            }))
        else:
            # view_signatures = set()
            # Bug Fix: If we use set, we cannot differ two GUI pages with different number of similar views
            #   This fix will bring more new GUI pages.
            view_signatures = []
            for view in self.views:
                view_signature = DeviceState.__get_view_signature(view)
                if view_signature:
                    # view_signatures.add(view_signature)
                    view_signatures.append(view_signature)
            return "%s{%s}" % (self.foreground_activity, ",".join(sorted(view_signatures)))

    def __get_content_free_state_str(self):
        if self.device.humanoid is not None:
            import json
            from xmlrpc.client import ServerProxy
            proxy = ServerProxy("http://%s/" % self.device.humanoid)
            state_str = proxy.render_content_free_view_tree(json.dumps({
                "view_tree": self.view_tree,
                "screen_res": [self.device.display_info["width"],
                               self.device.display_info["height"]]
            }))
        else:
            view_signatures = set()
            for view in self.views:
                view_signature = DeviceState.__get_content_free_view_signature(view)
                if view_signature:
                    view_signatures.add(view_signature)
            state_str = "%s{%s}" % (self.foreground_activity, ",".join(sorted(view_signatures)))
        import hashlib
        return hashlib.md5(state_str.encode('utf-8')).hexdigest()

    def get_content_free_state_plain_str(self):
        """
        get the content-free plain state str (do not compute hash value)
        :return: str
        """
        view_signatures = set()
        for view in self.views:
            view_signature = DeviceState.__get_content_free_view_signature(view)
            if view_signature:
                view_signatures.add(view_signature)
        state_str = "%s{%s}" % (self.foreground_activity, ",".join(sorted(view_signatures)))
        return state_str

    def __get_structure_free_state_str(self):
        """
        Only consider the foreground activity, window stack length, drawer view is opened or not, and the first level
        of children views.
        :return:
        """

        window_stack_len = len(self.window_stack)

        drawer_view_is_opened = "True" if self.__drawer_view_is_opened else "False"

        children_views_of_current_state = \
            self.__get_sole_child_view_2(self.view_tree)['children']

        view_signatures = []
        for child_view in children_views_of_current_state:
            view_signature = DeviceState.__get_content_free_view_signature(child_view)
            if view_signature:
                view_signatures.append(view_signature)

        state_str = "%s{%s}{%s}{%s}" % (self.foreground_activity,
                                        drawer_view_is_opened,
                                        str(window_stack_len),
                                        ",".join(sorted(view_signatures)))
        import hashlib
        return hashlib.md5(state_str.encode('utf-8')).hexdigest()

    def __get_search_content(self):
        """
        get a text for searching the state
        :return: str
        """
        words = [",".join(self.__get_property_from_all_views("resource_id")),
                 ",".join(self.__get_property_from_all_views("text"))]
        return "\n".join(words)

    def __get_property_from_all_views(self, property_name):
        """
        get the values of a property from all views
        :return: a list of property values
        """
        property_values = set()
        for view in self.views:
            property_value = DeviceState.__safe_dict_get(view, property_name, None)
            if property_value:
                property_values.add(property_value)
        return property_values

    def save2dir(self, output_dir):
        try:

            output_dir = os.path.join(output_dir, "states")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            dest_state_json_path = "%s/state_%s.json" % (output_dir, self.tag)
            if self.device.adapters[self.device.minicap]:
                dest_screenshot_path = "%s/screen_%s.jpg" % (output_dir, self.tag)
            else:
                dest_screenshot_path = "%s/screen_%s.png" % (output_dir, self.tag)
            state_json_file = open(dest_state_json_path, "w")
            state_json_file.write(self.to_json())
            state_json_file.close()
            # print("****screenshot path: %s" % dest_screenshot_path)
            # print("****state json path: %s" % state_json_file)

            shutil.copyfile(self.screenshot_path, dest_screenshot_path)
            self.screenshot_path = dest_screenshot_path
            self.json_state_path = dest_state_json_path

        except Exception as e:
            self.device.logger.warning(e)

    def save_view_img(self, view_dict, output_dir):

        try:
            output_dir = os.path.join(output_dir, "views")

            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            view_str = view_dict['view_str']
            tag = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            tag += "_" + str(DeviceState.unique_event_view_file_id)
            DeviceState.unique_event_view_file_id += 1

            if self.device.adapters[self.device.minicap]:
                view_file_path = "%s/view_%s_%s.jpg" % (output_dir, view_str, tag)
            else:
                # view_file_path = "%s/view_%s.png" % (output_dir, view_str)
                view_file_path = "%s/view_%s_%s.png" % (output_dir, view_str, tag)

            from PIL import Image
            # Load the original image:
            view_bound = view_dict['bounds']
            original_img = Image.open(self.screenshot_path)

            # TODO just for debugging, could be removed
            # image = cv2.imread(self.screenshot_path)
            # cv2.rectangle(image, tuple(view_bound[0]), tuple(view_bound[1]), COLOR_RED_TUPLE, 2)
            # cv2.imwrite(self.screenshot_path + "-checked.png", image)

            # view bound should be in original image bound
            view_img = original_img.crop((min(original_img.width - 1, max(0, view_bound[0][0])),
                                          min(original_img.height - 1, max(0, view_bound[0][1])),
                                          min(original_img.width, max(0, view_bound[1][0])),
                                          min(original_img.height, max(0, view_bound[1][1]))))
            view_img.save(view_file_path)

            return view_file_path

        except Exception as e:
            self.device.logger.warning(e)

    def is_different_from(self, another_state):
        """
        compare this state with another
        @param another_state: DeviceState
        @return: boolean, true if this state is different from other_state
        """
        return self.state_str != another_state.state_str

    #
    def is_structure_different_from(self, another_state):
        """
        compare this state with another in terms of structure
        :param another_state: DeviceState or structure_str of DeviceState
        :return: boolean, true if this state is different from other_state
        """
        if isinstance(another_state, DeviceState):
            return self.structure_str != another_state.structure_str
        elif isinstance(another_state, str):
            return self.structure_str != another_state
        else:
            return False

    #
    def is_activity_different_from(self, another_state):
        """
        compare this state with another in terms of foreground activity
        :param another_state:
        :return:
        """
        if isinstance(another_state, DeviceState):
            return self.foreground_activity != another_state.foreground_activity
        else:
            return False

    #
    def update_state_type(self, event_type):
        """
        update the state type according the event that reaches this state
        :param event_type:
        :return:
        """
        if event_type is None:
            return
        if (self.state_type is None) and (event_type in STATE_TYPE_BY_EXPLORE):
            self.state_type = STATE_TYPE_BY_EXPLORE
        elif (self.state_type is None) and (event_type in STATE_TYPE_BY_SCRIPT):
            self.state_type = STATE_TYPE_BY_SCRIPT
        elif ((self.state_type == STATE_TYPE_BY_EXPLORE) and (event_type in STATE_TYPE_BY_SCRIPT)) or \
                ((self.state_type == STATE_TYPE_BY_SCRIPT) and (event_type in STATE_TYPE_BY_EXPLORE)):
            self.state_type = STATE_TYPE_BY_BOTH
        return

    #
    def update_path_events(self, parent_state, event):
        # update path events
        path_events = copy.deepcopy(parent_state.get_last_path_events())
        path_events.append(event)
        self.last_path_events_from_entry_state = path_events
        # update path states
        path_states = copy.deepcopy(parent_state.get_last_path_states())
        path_states.append(self.structure_str)
        self.last_path_states_from_entry_state = path_states
        # create the dict
        path_events_dict = {
            "path_len": len(path_events),
            "path_events": path_events,
            "path_states": path_states
        }
        self.execution_path_events_set_from_entry_state.append(path_events_dict)

    def get_last_path_states(self):
        return self.last_path_states_from_entry_state

    # only for debugging
    def log_execution_path_events(self, path_events):
        print("[", end='')
        for event in path_events:
            event_str = event.get_event_str(self)
            print(event_str)
        print("]")

    def log_execution_path_events_info(self):
        self.logger.info("the last execution path events from entry state:")
        self.log_execution_path_events(self.last_path_events_from_entry_state)
        self.logger.info("all path events from entry state:")
        print("[", end='')
        for path_events in self.execution_path_events_set_from_entry_state:
            self.log_execution_path_events(path_events["path_events"])
        print("]")

    # End

    #
    def get_all_path_events(self):
        """
        get the set of path events
        :return: list[dict], the list of path events
        """
        return self.execution_path_events_set_from_entry_state

    #
    def get_last_path_events(self):
        """
        get the last path events
        :return: list, the list of path events
        """
        return self.last_path_events_from_entry_state

    #
    def get_shortest_path_events(self):
        """
        get the shortest path from the path events set
        :return: path events, the shortest path events
        :return: path states, the states along this path events
        """
        min_path_len = sys.maxsize
        shortest_paths = []
        for path in self.execution_path_events_set_from_entry_state:
            path_len = path["path_len"]
            if path_len <= min_path_len:
                min_path_len = path_len
                shortest_paths.append(path)
        rand_int = randint(0, len(shortest_paths) - 1)
        shortest_path = shortest_paths[rand_int]
        path_events = shortest_path["path_events"]
        path_states = shortest_path["path_states"]
        # TODO do we need to check None for shortest_path?
        return path_events, path_states

    #
    def is_script_state(self):
        if self.state_type == STATE_TYPE_BY_SCRIPT or self.state_type == STATE_TYPE_BY_BOTH:
            return True
        else:
            return False

    #
    def is_explore_state(self):
        if self.state_type == STATE_TYPE_BY_EXPLORE or self.state_type == STATE_TYPE_BY_BOTH:
            return True
        else:
            return False

    #
    def contain_child_with_text(self, view_dict, child_text_re):
        """
        check whether the view dict of this state has a child view whose text matches child_text
        :param view_dict: the view dict to check
        :param child_text_re: the regex of child text
        :return:
        """
        all_children: Set[int] = self.get_all_children(view_dict)
        for child_view_id in all_children:
            child_view = self.views[child_view_id]
            if child_text_re and safe_re_match(child_text_re, child_view['text']):
                return True
        return False

    @staticmethod
    def __get_view_signature(view_dict):
        """
        get the signature of the given view
        @param view_dict: dict, an element of list DeviceState.views
        @return:
        """
        if 'signature' in view_dict:
            return view_dict['signature']

        view_text = DeviceState.__safe_dict_get(view_dict, 'text', "None")
        if view_text is None or len(view_text) > 50:
            view_text = "None"

        # if ".EditText" in view_dict['class']:
        #     # we ignore the text of ".EditTex" for its signature
        #     signature = "[class]%s[resource_id]%s[text]%s[%s,%s,%s]" % \
        #                 (DeviceState.__safe_dict_get(view_dict, 'class', "None"),
        #                  DeviceState.__safe_dict_get(view_dict, 'resource_id', "None"),
        #                  "None",
        #                  DeviceState.__key_if_true(view_dict, 'enabled'),
        #                  DeviceState.__key_if_true(view_dict, 'checked'),
        #                  DeviceState.__key_if_true(view_dict, 'selected')
        #                  )
        # else:

        signature = "[class]%s[resource_id]%s[content_desc]%s[text]%s[%s,%s,%s]" % \
                    (DeviceState.__safe_dict_get(view_dict, 'class', "None"),
                     DeviceState.__safe_dict_get(view_dict, 'resource_id', "None"),
                     DeviceState.__safe_dict_get(view_dict, 'content_description', "None"),
                     view_text,
                     DeviceState.__key_if_true(view_dict, 'enabled'),
                     DeviceState.__key_if_true(view_dict, 'checked'),
                     DeviceState.__key_if_true(view_dict, 'selected')
                     )

        view_dict['signature'] = signature
        return signature

    @staticmethod
    def get_view_property_values(view_dict):
        """
        Get the property values of the given view. This is one abstraction strategy for a view.
        @param view_dict: dict, an element of list DeviceState.views
        @return: str
        """

        if DeviceState.include_content_desc:
            property_values = "[class]%s[resource_id]%s[content_desc]%s[%s,%s,%s,%s]" % \
                              (DeviceState.__safe_dict_get(view_dict, 'class', "None"),
                               DeviceState.__safe_dict_get(view_dict, 'resource_id', "None"),
                               DeviceState.__safe_dict_get(view_dict, 'content_description', "None"),
                               DeviceState.__key_if_true(view_dict, 'clickable'),
                               DeviceState.__key_if_true(view_dict, 'checkable'),
                               DeviceState.__key_if_true(view_dict, 'long_clickable'),
                               DeviceState.__key_if_true(view_dict, "scrollable")
                               )
        else:
            property_values = "[class]%s[resource_id]%s[%s,%s,%s,%s]" % \
                              (DeviceState.__safe_dict_get(view_dict, 'class', "None"),
                               DeviceState.__safe_dict_get(view_dict, 'resource_id', "None"),
                               DeviceState.__key_if_true(view_dict, 'clickable'),
                               DeviceState.__key_if_true(view_dict, 'checkable'),
                               DeviceState.__key_if_true(view_dict, 'long_clickable'),
                               DeviceState.__key_if_true(view_dict, "scrollable")
                               )

        return property_values

    @staticmethod
    def __get_content_free_view_signature(view_dict):
        """
        get the content-free signature of the given view. This is one abstraction strategy for a view.
        @param view_dict: dict, an element of list DeviceState.views
        @return:
        """
        if 'content_free_signature' in view_dict:
            return view_dict['content_free_signature']

        if DeviceState.include_content_desc:
            content_free_signature = "[class]%s[resource_id]%s[content_desc]%s" % \
                                     (DeviceState.__safe_dict_get(view_dict, 'class', "None"),
                                      DeviceState.__safe_dict_get(view_dict, 'resource_id', "None"),
                                      DeviceState.__safe_dict_get(view_dict, 'content_description', "None")
                                      )
        else:
            content_free_signature = "[class]%s[resource_id]%s" % \
                                     (DeviceState.__safe_dict_get(view_dict, 'class', "None"),
                                      DeviceState.__safe_dict_get(view_dict, 'resource_id', "None")
                                      )
        view_dict['content_free_signature'] = content_free_signature
        return content_free_signature

    def __get_view_str(self, view_dict):
        """
        get a string which can represent the given view
        @param view_dict: dict, an element of list DeviceState.views
        @return:
        """
        if 'view_str' in view_dict:
            return view_dict['view_str']
        view_signature = DeviceState.__get_view_signature(view_dict)
        parent_strs = []
        for parent_id in self.get_all_ancestors(view_dict):
            parent_strs.append(DeviceState.__get_view_signature(self.views[parent_id]))
        parent_strs.reverse()
        child_strs = []
        for child_id in self.get_all_children(view_dict):
            child_strs.append(DeviceState.__get_view_signature(self.views[child_id]))
        child_strs.sort()
        view_str = "Activity:%s\nSelf:%s\nParents:%s\nChildren:%s" % \
                   (self.foreground_activity, view_signature, "//".join(parent_strs), "||".join(child_strs))
        import hashlib
        view_str = hashlib.md5(view_str.encode('utf-8')).hexdigest()
        # use 'sibling_id' is better than 'temp_id'
        #   ('temp_id' is very likely to be changed when some views are changed)
        view_dict['view_str'] = view_str + "_" + str(view_dict['sibling_id'])
        return view_str

    def __get_view_structure(self, view_dict):
        """
        get the structure of the given view
        :param view_dict: dict, an element of list DeviceState.views
        :return: dict, representing the view structure
        """
        if 'view_structure' in view_dict:
            return view_dict['view_structure']
        width = DeviceState.get_view_width(view_dict)
        height = DeviceState.get_view_height(view_dict)
        class_name = DeviceState.__safe_dict_get(view_dict, 'class', "None")
        children = {}

        root_x = view_dict['bounds'][0][0]
        root_y = view_dict['bounds'][0][1]

        child_view_ids = self.__safe_dict_get(view_dict, 'children')
        if child_view_ids:
            for child_view_id in child_view_ids:
                child_view = self.views[child_view_id]
                child_x = child_view['bounds'][0][0]
                child_y = child_view['bounds'][0][1]
                relative_x, relative_y = child_x - root_x, child_y - root_y
                children["(%d,%d)" % (relative_x, relative_y)] = self.__get_view_structure(child_view)

        view_structure = {
            "%s(%d*%d)" % (class_name, width, height): children
        }
        view_dict['view_structure'] = view_structure
        return view_structure

    @staticmethod
    def __key_if_true(view_dict, key):
        return key if (key in view_dict and view_dict[key]) else ""

    @staticmethod
    def __safe_dict_get(view_dict, key, default=None):
        return view_dict[key] if (key in view_dict) else default

    @staticmethod
    def __safe_dict_set(view_dict, key, value):
        if key in view_dict:
            view_dict[key] = value

    @staticmethod
    def get_view_id(view_dict):
        return view_dict['temp_id']

    @staticmethod
    def get_view_center(view_dict):
        """
        return the center point in a view
        @param view_dict: dict, an element of DeviceState.views
        @return: a pair of int
        """
        bounds = view_dict['bounds']
        return (bounds[0][0] + bounds[1][0]) / 2, (bounds[0][1] + bounds[1][1]) / 2

    @staticmethod
    def get_view_width(view_dict):
        """
        return the width of a view
        @param view_dict: dict, an element of DeviceState.views
        @return: int
        """
        bounds = view_dict['bounds']
        return int(math.fabs(bounds[0][0] - bounds[1][0]))

    @staticmethod
    def get_view_height(view_dict):
        """
        return the height of a view
        @param view_dict: dict, an element of DeviceState.views
        @return: int
        """
        bounds = view_dict['bounds']
        return int(math.fabs(bounds[0][1] - bounds[1][1]))

    def get_all_ancestors(self, view_dict):
        """
        Get temp view ids of the given view's ancestors
        :param view_dict: dict, an element of DeviceState.views
        :return: list of int, each int is an ancestor node id
        """
        result = []
        parent_id = self.__safe_dict_get(view_dict, 'parent', -1)
        if 0 <= parent_id < len(self.views):
            result.append(parent_id)
            result += self.get_all_ancestors(self.views[parent_id])
        return result

    def get_all_children(self, view_dict):
        """
        Get temp view ids of the given view's children
        :param view_dict: dict, an element of DeviceState.views
        :return: set of int, each int is a child node id
        """
        children = self.__safe_dict_get(view_dict, 'children')
        if not children:
            return set()
        children = set(children)
        # print("--children before loop")
        # print(children)
        for child in children:
            # print("child id: %d" % child)

            if child >= len(self.views):
                # Hot fix: "list index out of range" for self.views[child]
                continue
            children_of_child = self.get_all_children(self.views[child])

            # print("children of this child: ")
            # print(children_of_child)
            children = children.union(children_of_child)

        # print("--return total children:")
        # print(children)
        return children

    def get_app_activity_depth(self, app):
        """
        Get the depth of the app's activity in the activity stack
        :param app: App
        :return: the depth of app's activity, -1 for not found
        """
        depth = 0
        for activity_str in self.activity_stack:
            if app.package_name in activity_str:
                return depth
            depth += 1
        return -1

    def get_possible_input(self, ignore_windows_script=None):
        """
        Get a list of possible input events for this state
        :return: list of InputEvent
        """
        if self.possible_events:
            return [] + self.possible_events

        possible_events = []
        enabled_view_ids = []
        touch_exclude_view_ids = set()

        for view_dict in self.views:

            if self.is_date_time_picker_page:
                # Only enable "OK" and "Cancel" buttons
                #   'OK': {'class': 'android.widget.Button', 'resource_id': 'android:id/button1', 'text': 'OK'}
                #   'Cancel': {'class': 'android.widget.Button', 'resource_id': 'android:id/button2', 'text': 'Cancel'}
                if view_dict['class'] == 'android.widget.Button' and \
                        view_dict['resource_id'] == 'android:id/button1' and view_dict['text'] == 'OK':
                    pass
                elif view_dict['class'] == 'android.widget.Button' and \
                        view_dict['resource_id'] == 'android:id/button2' and view_dict['text'] == 'Cancel':
                    pass
                else:
                    continue

            if self.__drawerlayout_primary_content_view_id is not None and \
                    view_dict['temp_id'] == self.__drawerlayout_primary_content_view_id:
                self.__drawerlayout_exclude_primary_content_view_ids = self.get_all_children(view_dict)
                continue
            if view_dict['temp_id'] in self.__drawerlayout_exclude_primary_content_view_ids:
                # exclude the primary content view of drawerlayout if exists
                continue

            if self.__safe_dict_get(view_dict, 'resource_id') in ['android:id/navigationBarBackground',
                                                                  'android:id/statusBarBackground']:
                # exclude navigation bar background views
                continue

            if not self.__safe_dict_get(view_dict, 'enabled'):
                # exclude not enabled views
                continue

            if not self.__safe_dict_get(view_dict, 'visible'):
                # exclude not visible views
                continue

            # Avoid language, locale setting in the app
            # if self.app_package_name == 'com.ichi2.anki' and self.foreground_activity == 'com.ichi2.anki/.Preferences':
            #     if view_dict['class'] == 'android.widget.LinearLayout' and view_dict['clickable']:
            #         view_content_sensitive_str = self.get_view_content_sensitive_str(view_dict)
            #         if 'System language' in view_content_sensitive_str and \
            #                 'Language' in view_content_sensitive_str:
            #             # avoid language setting
            #             continue
            #
            # if self.app_package_name == 'net.gsantner.markor' and self.foreground_activity == 'net.gsantner.markor/.activity.SettingsActivity':
            #     if view_dict['class'] == 'android.widget.LinearLayout' and view_dict['clickable']:
            #         view_content_sensitive_str = self.get_view_content_sensitive_str(view_dict)
            #         if 'Language' in view_content_sensitive_str:
            #             # avoid language setting
            #             continue

            # if 'skytube.extra' in self.app_package_name and self.foreground_activity == 'free.rm.skytube.extra/free.rm.skytube.gui.activities.PreferencesActivity':
            #     if view_dict['class'] == 'android.widget.LinearLayout' and view_dict['clickable']:
            #         view_content_sensitive_str = self.get_view_content_sensitive_str(view_dict)
            #         if 'Preferred Region' in view_content_sensitive_str or 'Preferred Language(s)' in view_content_sensitive_str:
            #             # avoid region and language setting
            #             continue

            if 'fantastischmemo' in self.app_package_name and self.foreground_activity == 'org.liberty.android.fantastischmemo/.ui.OptionScreen':
                if view_dict['class'] == 'android.widget.LinearLayout' and view_dict['clickable']:
                    view_content_sensitive_str = self.get_view_content_sensitive_str(view_dict)
                    if 'Interface language' in view_content_sensitive_str:
                        # avoid region and language setting
                        continue

            enabled_view_ids.append(view_dict['temp_id'])

        # reverse the tree and conduct bottom-up checking
        enabled_view_ids.reverse()

        print("clickable events:")

        for view_id in enabled_view_ids:
            if self.__safe_dict_get(self.views[view_id], 'clickable'):

                # TODO application specific event encoding
                if "org.y20k.transistor" in self.foreground_activity and \
                        self.views[view_id]['resource_id'] == "org.y20k.transistor:id/player_sheet":
                    possible_events.append(ScrollEvent(view=self.views[view_id], direction="UP"))

                if "free.rm.skytube.gui.activities.MainActivity" in self.foreground_activity and \
                        self.views[view_id]['resource_id'] == "android:id/button2":
                    # click the "LATER" button to skip new version update
                    possible_events.clear()
                    possible_events.append(TouchEvent(view=self.views[view_id]))
                    self.possible_events = possible_events
                    return [] + possible_events

                if "org.tasks.debug/com.todoroo.astrid.activity.TaskListActivity" in self.foreground_activity and \
                        (self.views[view_id]['text'] == "‎‎Pick from storage" or
                         self.views[view_id]['text'] == "Add location"):
                    pass

                else:
                    view_class = self.__safe_dict_get(self.views[view_id], 'class')
                    if ".widget.EditText" in view_class or ".widget.ListView" in view_class:
                        # Do not generate the "click" event for EditText, ListView
                        continue

                    if ignore_windows_script is not None and \
                            ignore_windows_script.is_ignored_view(self, self.views[view_id], 'clickable'):
                        # do not add this view if ignored
                        pass
                    else:
                        possible_events.append(TouchEvent(view=self.views[view_id]))
                        print(self.__get_view_signature(self.views[view_id]) + "\n")

                    touch_exclude_view_ids.add(view_id)

                    # print("view_id: %d" % view_id)
                    # print(touch_exclude_view_ids)
                    # fix a bug: add union return values
                    touch_exclude_view_ids = touch_exclude_view_ids.union(self.get_all_children(self.views[view_id]))
                    # print(touch_exclude_view_ids)
                    # print(self.get_all_children(self.views[view_id]))

        print("scrollable events:")
        for view_id in enabled_view_ids:

            if self.__safe_dict_get(self.views[view_id], 'scrollable'):

                if ".widget.Spinner" in self.views[view_id]['class'] or \
                        ".widget.ListView" in self.views[view_id]['class']:
                    # Do not generate scroll events for Spinner, ListView
                    continue

                possible_events.append(ScrollEvent(view=self.views[view_id], direction="UP"))
                possible_events.append(ScrollEvent(view=self.views[view_id], direction="DOWN"))
                possible_events.append(ScrollEvent(view=self.views[view_id], direction="LEFT"))
                possible_events.append(ScrollEvent(view=self.views[view_id], direction="RIGHT"))

                print(self.__get_view_signature(self.views[view_id]) + "\n")

        print("checkable events:")
        for view_id in enabled_view_ids:
            if self.__safe_dict_get(self.views[view_id], 'checkable') and \
                    not self.__safe_dict_get(self.views[view_id], 'clickable'):
                # only generate checkable event if the view is not clickable (avoid duplicate event generation)
                if ignore_windows_script is not None and \
                        ignore_windows_script.is_ignored_view(self, self.views[view_id], 'checkable'):
                    # do not add this view if ignored
                    pass
                else:
                    possible_events.append(TouchEvent(view=self.views[view_id]))
                    print(self.__get_view_signature(self.views[view_id]) + "\n")

                touch_exclude_view_ids.add(view_id)
                # fix a bug: add union return values
                touch_exclude_view_ids = touch_exclude_view_ids.union(self.get_all_children(self.views[view_id]))

                # print(self.get_all_children(self.views[view_id]))

        print("long_clickable events:")

        for view_id in enabled_view_ids:
            if self.__safe_dict_get(self.views[view_id], 'long_clickable') and \
                    not ('.widget.EditText' in self.__safe_dict_get(self.views[view_id], 'class')):
                # do not generate the "click" event for EditText

                if ignore_windows_script is not None and \
                        ignore_windows_script.is_ignored_view(self, self.views[view_id], 'long_clickable'):
                    # do not add this view if ignored
                    pass
                else:
                    possible_events.append(LongTouchEvent(view=self.views[view_id]))
                    print(self.__get_view_signature(self.views[view_id]) + "\n")

        print("editable events:")

        for view_id in enabled_view_ids:
            if self.__safe_dict_get(self.views[view_id], 'editable'):
                # TODO application specific event encoding

                if "org.y20k.transistor" in self.app_package_name or \
                        "de.rampro.activitydiary" in self.app_package_name:
                    # and
                    #     self.views[view_id]['resource_id'] == "org.y20k.transistor:id/dialog_add_station_input":
                    # input_text = "https://sverigesradio.se/topsy/direkt/212-hi-mp3.m3u"
                    # possible_events.append(SetTextEvent(view=self.views[view_id], text=input_text))
                    input_texts = ["HelloWorld"]

                elif 'be.digitalia.fosdem' in self.app_package_name:
                    # set specific text inputs
                    input_texts = ["Aaron"]

                elif 'nl.mpcjanssen.simpletask' in self.app_package_name or \
                        'net.gsantner.markor' in self.app_package_name:
                    # set specific text inputs
                    input_texts = ["Hello", ""]

                else:
                    input_texts = ["Hello", "123"]

                possible_events.append(SetTextEvent(view=self.views[view_id],
                                                    text=input_texts[randint(0, len(input_texts) - 1)]))

                touch_exclude_view_ids.add(view_id)
                # TODO figure out what event can be sent to editable views

                print(self.__get_view_signature(self.views[view_id]) + "\n")

                pass

        print("other events:")

        # for those views that (1) have not been handled, and (2) are leaf views, generate touch events
        for view_id in enabled_view_ids:
            if view_id in touch_exclude_view_ids:
                continue
            children = self.__safe_dict_get(self.views[view_id], 'children')
            if children and len(children) > 0:
                continue

            # fix a possible bug: we still need to check the property
            # before we add them into "possible_events"
            if self.__safe_dict_get(self.views[view_id], 'clickable') or \
                    self.__safe_dict_get(self.views[view_id], 'checkable'):

                if ignore_windows_script is not None and \
                        ignore_windows_script.is_ignored_view(self, self.views[view_id]):
                    # do not add this view if ignored
                    pass
                else:
                    possible_events.append(TouchEvent(view=self.views[view_id]))
                    print(self.__get_view_signature(self.views[view_id]) + "\n")

        # input("Enter:")

        # For old Android navigation bars
        # possible_events.append(KeyEvent(name="MENU"))

        self.possible_events = possible_events
        return [] + possible_events

    def contain_input_event(self, input_event):
        """
        Check whether the state may contain the input event
        :param input_event: the input event
        :return:
        """
        possible_events = self.get_possible_input()
        for tmp_event in possible_events:
            if DeviceState.equal_input_events(tmp_event, input_event):
                return True
        return False

    @staticmethod
    def equal_input_events(input_event_1, input_event_2):

        """
        check whether two input events
        :param input_event_1:
        :param input_event_2:
        :return:
        """
        if input_event_1.event_type == input_event_2.event_type:
            input_event_1_views = input_event_1.get_views()
            input_event_2_views = input_event_2.get_views()
            if len(input_event_1_views) == len(input_event_2_views):
                equal = all(
                    DeviceState.get_view_property_values(tmp_view) == DeviceState.get_view_property_values(view)
                    for tmp_view, view in zip(input_event_1_views, input_event_2_views))
                if equal:
                    return True
        return False

    def get_gui_page_type(self, gui_page_types_info):
        """
        get the gui page type of given device state
        :param gui_page_types_info:
        :return:
        """
        default_page_type = "Unknown"

        for page_type in gui_page_types_info:

            target_views = gui_page_types_info[page_type]
            ret_views = []

            if self.foreground_activity != target_views[0]['activity']:
                # continue if the activities are not equal
                continue

            for target_view in target_views:
                for view_dict in self.views:
                    if DeviceState.are_views_equal(target_view, view_dict):
                        ret_views.append(view_dict)

            if len(ret_views) == len(target_views):
                default_page_type = page_type
                break

        # set the page type
        self.gui_page_type = default_page_type
        return default_page_type
