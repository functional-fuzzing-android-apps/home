# This file records the GUI views that will be ignored during semantic checking
import logging
import re
from typing import Dict, List


class ConfigurationScript(object):
    """
    Specify the GUI views that will be ignored.
    The script includes three types of ignored views:
        (1) ignore_view_widget, the view that will be ignored
        (2) ignore_view_diff, the view diff that will be ignored for computing gui difference
        (3) ignore_view_order, the order of view's children will be ignored for computing gui difference
    """

    script_grammar = {
        'activity_name': {

        }
    }

    IGNORE_VIEW_DICT = "ignore_view_dict"
    IGNORE_VIEW_DIFF = "ignore_view_diff"
    IGNORE_VIEW_ORDER = "ignore_view_order"

    VIEWS_KEY = "views"
    SCREENS_KEY = "screens"

    def __init__(self, script_dict):

        self.logger = logging.getLogger(self.__class__.__name__)
        self.script_dict = script_dict
        self.screens_info_table = self.parse_screens_info(script_dict)

    def parse_screens_info(self, script_dict):
        """
        parse the script to get the screen info table
        :param script_dict:
        :return:
        """
        # data structure:
        #   str: the activity name
        #   List: screens with the activity name
        screen_info_table: Dict[str, List[Dict]] = {}

        if ConfigurationScript.VIEWS_KEY in script_dict and \
                ConfigurationScript.SCREENS_KEY in script_dict:

            views = script_dict[ConfigurationScript.VIEWS_KEY]
            screens = script_dict[ConfigurationScript.SCREENS_KEY]

            for screen_name in screens.keys():
                screen_info = screens[screen_name]
                views_of_screen = screen_info['views']
                for view_name in views_of_screen:
                    if view_name not in views.keys():
                        print("script format error: the view \"%s\" is not in the script." % view_name)
                        exit(0)
                if "activity" not in screen_info:
                    print("script format error: missing activity info.")

                screen_info['view_dicts'] = self._get_views_of_screen(views, views_of_screen)

                if screen_info['activity'] not in screen_info_table:
                    screen_info_table[screen_info['activity']] = [{screen_name: screen_info}]
                else:
                    screen_info_table[screen_info['activity']].append({screen_name: screen_info})
        return screen_info_table

    def _get_views_of_screen(self, all_views, views_of_screen: List[str]):
        views = []
        for view_name in views_of_screen:
            views.append(all_views[view_name])
        return views

    def get_screen_name(self, activity_name_of_state, views_of_state):
        candidate_screens = self.screens_info_table[activity_name_of_state]
        for screen in candidate_screens:
            screen_name = list(screen.keys())[0]
            view_dicts_of_screen = screen[screen_name]['view_dicts']
            matched = True

            for view in view_dicts_of_screen:
                if not self.has_target_views(view, views_of_state):
                    # stop if the state does not contain ``view``
                    #   i.e., this state does not equal to ``screen_name``
                    matched = False
                    break

            if matched:
                # Return ``screen_name`` if the state contains all views of this ``screen``
                return screen_name

        # Return None if the state does not match with any screens
        return None

    def has_target_views(self, target_view, views_of_state):
        target_view_keys = list(target_view.keys())

        for view in views_of_state:
            found = True

            # is ``view`` matched with ``target_view``
            for key in target_view_keys:
                if view[key] != target_view[key]:
                    # stop if at least one key-value does not match
                    found = False
                    break

            if found:
                # all the key-values are matched between ``view`` and ``target_view``
                return True

        # all views in this state does not match with the target view
        return False

    def get_views_with_children_order_ignored(self, activity_name):

        target_views = []

        if activity_name in self.script_dict:
            ignored_views = self.script_dict[activity_name]
            for view_key in ignored_views:
                if ConfigurationScript.IGNORE_VIEW_ORDER in view_key:
                    target_views.append(ignored_views[view_key])

        return target_views if len(target_views) != 0 else None

    def is_ignored_view_dict(self, activity_name, target_view_dict):
        """
        check whether the target view dict should be ignored
        :param activity_name:   the activity that this target view dict belongs to
        :param target_view_dict:    the target view dict
        :return: boolean
        """

        if activity_name in self.script_dict:
            ignore_dicts = self.script_dict[activity_name]
            for key in ignore_dicts:
                if ConfigurationScript.IGNORE_VIEW_DICT in key:
                    class_of_ignore_view_dict = ignore_dicts[key]['class']
                    if class_of_ignore_view_dict == target_view_dict['class']:
                        resource_id_of_ignore_view_dict = ignore_dicts[key]['resource_id']
                        text_regex = ignore_dicts[key]['text_regex']

                        if resource_id_of_ignore_view_dict is not None and \
                                resource_id_of_ignore_view_dict == target_view_dict['resource_id']:
                            return True

                        if resource_id_of_ignore_view_dict is None and \
                                text_regex is not None:
                            match_result = re.search(text_regex, target_view_dict['text'])
                            if match_result is not None:
                                return True

            return False
        else:
            return False

    def is_ignored_view_diff(self, activity_name, from_view_dict, to_view_dict):
        """
        check whether the given view diff should be ignored

        :param activity_name:
        :param from_view_dict:
        :param to_view_dict:
        :return:
        """
        if from_view_dict is None or to_view_dict is None:
            return False

        if activity_name in self.script_dict:

            # get the properties (class, resource_id, text) of target view diff
            class_of_target_view_diff = from_view_dict['class'] if \
                from_view_dict is not None else to_view_dict['class']

            resource_id_of_target_view_diff = from_view_dict['resource_id'] if \
                from_view_dict is not None else to_view_dict['resource_id']

            text_of_target_from_view_dict = from_view_dict['text'] if from_view_dict['text'] is not None else "None"
            text_of_target_to_view_dict = to_view_dict['text'] if to_view_dict['text'] is not None else "None"

            ignored_dicts = self.script_dict[activity_name]
            for view_key in ignored_dicts:

                if ConfigurationScript.IGNORE_VIEW_DIFF not in view_key:
                    continue

                view_diff_info = ignored_dicts[view_key]
                class_of_view_diff = view_diff_info['class']
                resource_id_of_view_diff = view_diff_info['resource_id']
                from_text_regex_of_view_diff = view_diff_info['from_text_regex']
                to_text_regex_of_view_diff = view_diff_info['to_text_regex']

                if class_of_view_diff == class_of_target_view_diff:
                    # Note that the view class is ALWAYS not null

                    if resource_id_of_target_view_diff is not None and \
                            resource_id_of_view_diff == resource_id_of_target_view_diff:
                        if from_text_regex_of_view_diff is not None and to_text_regex_of_view_diff is not None:
                            # check whether the text regex holds if the target view's resource id is none
                            match_result_1 = re.search(from_text_regex_of_view_diff, text_of_target_from_view_dict)
                            match_result_2 = re.search(to_text_regex_of_view_diff, text_of_target_to_view_dict)
                            if match_result_1 is not None and match_result_2 is not None:
                                return True

            return False
        else:
            return False


class IgnoreScriptSyntaxError(RuntimeError):
    """
    syntax error of DroidBotScript
    """
    pass
