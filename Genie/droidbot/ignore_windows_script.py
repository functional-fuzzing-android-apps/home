# This file ignore specific windows (e.g., Activities, Dialogs, Menus, etc.) during model construction.
import logging
import re
from typing import Dict

from droidbot.device_state import DeviceState


class IgnoreWindowsScript(object):
    """the script to define the GUI windows that will be ignored"""

    def __init__(self, script_dict):

        self.logger = logging.getLogger(self.__class__.__name__)
        self.script_dict = script_dict

        # list of activities to be ignored during model construction
        self.ignored_activities = []
        # list of views to be ignored during model construction
        #   str: the activity name
        #   Dict: the specified view
        self.ignored_views: Dict[str, Dict] = {}

        self.parse_script()

    def parse_script(self):
        for activity_name in self.script_dict.keys():
            ignore_views = self.script_dict[activity_name]
            if len(ignore_views) == 0:
                # ignore the activity if no views are specified
                self.ignored_activities.append(activity_name)
            else:
                # only ignore the given views in the activity
                self.ignored_views[activity_name] = ignore_views

    def is_ignored_window(self, target_activity_name):
        """
        check whether the given activity is to be ignored
        :param target_activity_name:
        :return:
        """
        if target_activity_name in self.ignored_activities:
            return True
        else:
            return False

    def is_ignored_view(self, current_state: DeviceState, target_view: Dict, intended_action=None):
        """
        check whether the given view is to be ignored
        :param current_state: the device state where the given view locates in
        :param target_view: the given view
        :param intended_action: the intended action on the given view
        :return:
        """
        current_activity_name = current_state.foreground_activity
        if current_activity_name in self.ignored_views:

            # get the target views for checking, which includes the target view itself and all its children views
            views_under_checking = [target_view]
            children_of_target_view = current_state.get_all_children(target_view)
            for child_id in children_of_target_view:
                views_under_checking.append(current_state.views[child_id])

            ignored_views = self.ignored_views[current_activity_name]
            for view in views_under_checking:
                for ignored_view_key in ignored_views:
                    ignored_view = ignored_views[ignored_view_key]

                    if view['class'] == ignored_view['class']:
                        # tODO need add more checking logics, currently incomplete
                        if view['resource_id'] is not None and ignored_view['resource_id'] is not None:
                            if ignored_view['text_regex'] is None:
                                if view['resource_id'] == ignored_view['resource_id']:
                                    return True
                            else:  # ignored_view['text_regex'] is not None:
                                if view['resource_id'] == ignored_view['resource_id']:
                                    if view['text'] is not None:
                                        match_result = re.search(ignored_view['text_regex'], view['text'])
                                        if match_result is not None:
                                            if 'action' not in ignored_view:
                                                return True
                                            else:   # 'action' in ignored_view
                                                if intended_action is not None and \
                                                        intended_action == ignored_view['action']:
                                                    return True

            return False
        else:
            return False

