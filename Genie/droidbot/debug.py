# This file uses to debug DroidMutator
import json
import logging
import os
import shutil
from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, List

from droidbot.app import App
from droidbot.device import Device
from droidbot.device_state import DeviceState
from droidbot.gui_test import GUITestCase, TEST_TAG_MUTANT_TEST, TEST_TAG_SEED_TEST
from droidbot.input_event import InputEvent
from droidbot.utg import UTG
from droidbot.utils import replace_file


class DroidMutatorDebugger(object):

    def __init__(self, apk_path=None, output_dir=None, mutant_dir=None, seed_dir=None, views_json_file=None):

        self.logger = logging.getLogger(self.__class__.__name__)
        self.device = Device(device_serial='emulator-dummy', is_emulator=True, output_dir=output_dir)  # a dummy device object

        self.apk_path = apk_path
        self.output_dir = output_dir
        self.mutant_dir = mutant_dir
        self.views_json_file = views_json_file
        self.seed_dir = seed_dir

        self.app = App(self.apk_path, self.output_dir)
        self.original_utg = UTG(device=self.device, app=self.app, random_input=None)
        self.clustered_utg = UTG(device=self.device, app=self.app, random_input=None)

    def cluster_original_utg(self):

        # recover the original utg
        self.original_utg.recover_original_utg(self.output_dir)
        # cluster the original utg
        self.clustered_utg.cluster_utg_structure(self.original_utg, output_clustered_utg=True)

        self.logger.info("The original utg is clustered.")

    @staticmethod
    def find_matched_event_views_on_utg(views_json_file, utg: UTG):

        # Start the recovery
        json_file = open(views_json_file, "r")
        views_to_match = json.load(json_file)
        json_file.close()

        matched_event_ids = []  # the critical events' ids for drawing

        for (from_state_str, to_state_str) in utg.G.edges:

            for event_str in utg.G[from_state_str][to_state_str]["events"]:
                event_dict = utg.G[from_state_str][to_state_str]["events"][event_str]
                input_event: InputEvent = event_dict["event"]
                event_id = event_dict["id"]

                views_of_event = input_event.get_views()
                view_of_event = views_of_event[0] if len(views_of_event) > 0 else None

                if view_of_event is None:
                    continue

                for view_name in views_to_match:

                    view_to_match = views_to_match[view_name]

                    matched = DeviceState.are_views_match(view_to_match, view_of_event)

                    if matched:
                        matched_event_ids.append(str(event_id))

        if len(matched_event_ids) != 0:
            # return true if all the specified views to match are matched
            return True
        else:
            return False

    @staticmethod
    def find_matched_state_views_on_utg(views_json_file, utg: UTG):

        # Start the recovery
        json_file = open(views_json_file, "r")
        views_to_match = json.load(json_file)
        json_file.close()

        matched_views = []  # the critical events' ids for drawing

        for state_str in utg.G.nodes():

            state: DeviceState = utg.G.nodes[state_str]["state"]
            state_views = state.views

            for view_dict in state_views:

                for view_name in views_to_match:

                    view_to_match = views_to_match[view_name]

                    matched = DeviceState.are_views_match(view_to_match, view_dict)

                    if matched:
                        matched_views.append(view_to_match)

        if len(matched_views) != 0:
            # return true if all the specified views to match are matched
            return True
        else:
            return False

    def check_seed_tests(self):

        base = Path(self.output_dir)
        seeds = [i for i in base.glob('seed-tests/seed-test-*')]  # get all seed tests in absolute path

        for seed in seeds:

            seed_test_dir = str(seed)
            # recover the seed test
            seed_test = GUITestCase(self.device, self.app, None,
                                    test_output_dir=seed_test_dir,
                                    test_tag=TEST_TAG_SEED_TEST).recover_test_case()

            if DroidMutatorDebugger.find_matched_event_views_on_utg(self.views_json_file, seed_test.utg):
                print("---------")
                print("[Matched Events] %s" % seed_test_dir)

            if DroidMutatorDebugger.find_matched_state_views_on_utg(self.views_json_file, seed_test.utg):
                print("---------")
                print("[Matched States] %s" % seed_test_dir)

    def draw(self):

        transition_annotation_info_dict: Dict[str, List[str]] = {}

        if self.seed_dir is not None and self.mutant_dir is not None:
            self.logger.warning("You cannot draw the seed test and mutant test at the same time")
            return

        # recover the original utg
        self.original_utg.recover_original_utg(self.output_dir)
        # cluster the original utg
        self.clustered_utg.cluster_utg_structure(self.original_utg, output_clustered_utg=True)

        print("\n\n\n\n")

        if self.seed_dir is not None:

            assert (
                   os.path.exists(self.seed_dir)
            ), "seed test dir does not exist!"

            transition_annotation_info = self.draw_seed_test_on_clustered_utg()
            transition_annotation_info_dict["red"] = transition_annotation_info

        if self.mutant_dir is not None:

            assert (
                os.path.exists(self.mutant_dir)
            ), "mutant test dir does not exist!"

            transition_annotation_info = self.draw_mutant_test_on_clustered_utg()
            transition_annotation_info_dict["red"] = transition_annotation_info

        if self.views_json_file is not None:
            assert (
                os.path.exists(self.views_json_file)
            ), "view file does not exist!"

            transition_annotation_info = self.draw_critical_views_on_clustered_utg()
            transition_annotation_info_dict["blue"] = transition_annotation_info

        if len(transition_annotation_info_dict) != 0:
            self.annotate_transitions_on_clustered_utg(self.clustered_utg, transition_annotation_info_dict)

    def draw_mutant_test_on_clustered_utg(self):
        """
        draw the mutant test on the clustered utg
        :param self:
        :return:
        """

        # recover the mutant and seed test
        mutant_test = GUITestCase(self.device, self.app, None,
                                  test_output_dir=self.mutant_dir,
                                  test_tag=TEST_TAG_MUTANT_TEST).recover_test_case()

        # collect the transition annotation info
        utg_event_ids_of_test, transition_annotation_info = \
            mutant_test.get_utg_event_ids_on_clustered_utg(self.clustered_utg)
        self.logger.warning("======")
        self.logger.warning("We find the mutant test: " + self.mutant_dir)
        self.logger.warning("the mutant test's utg ids: " + str(utg_event_ids_of_test))

        return transition_annotation_info

    def draw_seed_test_on_clustered_utg(self):
        """
        draw the seed test on the clustered utg
        :param self:
        :return:
        """

        # recover the seed test
        seed_test = GUITestCase(self.device, self.app, None,
                                test_output_dir=self.seed_dir,
                                test_tag=TEST_TAG_SEED_TEST).recover_test_case()

        self.logger.warning("======")
        # collect the transition annotation info
        utg_event_ids_of_test, transition_annotation_info = \
            seed_test.get_utg_event_ids_on_clustered_utg(self.clustered_utg)

        self.logger.warning("We find the seed test: " + self.seed_dir)
        self.logger.warning("the seed test's utg ids: " + str(utg_event_ids_of_test))

        return transition_annotation_info

    def draw_critical_views_on_clustered_utg(self):

        self.logger.warning("======")
        # collect the transition annotation info
        critical_event_ids, critical_event_info = self.find_critical_views_on_clustered_utg(self.views_json_file,
                                                                                            self.original_utg,
                                                                                            self.clustered_utg)
        self.logger.warning("we find critical event ids: ")
        self.logger.warning(str(critical_event_info))

        return critical_event_ids

    def annotate_transitions_on_clustered_utg(self, clustered_utg: UTG, transition_annotation_info):
        """
        annotate the gui test on the clustered utg
        :param clustered_utg:
        :param transition_annotation_info:
        :return:
        """

        # create a new file name
        new_file_name = "clustered_utg_with_annotated_test"
        utg_js_file_name = new_file_name + ".js"
        utg_json_file_name = new_file_name + ".json"

        # create the js file
        clustered_utg.output_utg_for_debug(self.output_dir,
                                           js_file=utg_js_file_name,
                                           json_file=utg_json_file_name,
                                           transition_annotation_info=transition_annotation_info)

        # create the index.html
        original_html_file_path = os.path.join(self.output_dir, "index.html")
        new_html_file_name = os.path.basename(original_html_file_path).replace(
            '.html',
            '_{}.html'.format(new_file_name))
        new_html_file_path = os.path.join(self.output_dir, new_html_file_name)

        if os.path.exists(original_html_file_path):
            # should always be true, just double check
            shutil.copyfile(original_html_file_path, new_html_file_path)
            replace_file(new_html_file_path, lambda s: s.replace('utg.js', utg_js_file_name))

    def find_critical_views_on_clustered_utg(self, views_json_file, original_utg: UTG, clustered_utg: UTG):

        # Start the recovery
        json_file = open(views_json_file, "r")
        views_data = json.load(json_file)
        json_file.close()

        critical_event_ids = []  # the critical events' ids for drawing
        critical_event_info = []  # the info of critical events for outputting

        for (from_state_str, to_state_str) in clustered_utg.G.edges:

            for event_str in clustered_utg.G[from_state_str][to_state_str]["events"]:
                event_dict = clustered_utg.G[from_state_str][to_state_str]["events"][event_str]
                input_event: InputEvent = event_dict["event"]
                event_id = event_dict["id"]

                # get this event's from_state_str on the original utg
                from_state_str_of_original_utg = event_dict["original_utg_from_state_str"]

                views_of_event = input_event.get_views()
                view_of_event = views_of_event[0] if len(views_of_event) > 0 else None

                if view_of_event is None:
                    continue

                for view_name in views_data:

                    view_dict = views_data[view_name]

                    matched = True

                    if "resource_id" in view_dict and view_dict['resource_id'] != view_of_event['resource_id']:
                        matched = False
                    elif "class" in view_dict and view_dict['class'] != view_of_event['class']:
                        matched = False
                    elif "text" in view_dict and view_dict['text'] != view_of_event['text']:
                        matched = False

                    if matched is True:
                        critical_event_ids.append(str(event_id))

                        # find the state from the original utg
                        from_state_of_critical_event: DeviceState = \
                            original_utg.get_node_by_state_str(from_state_str_of_original_utg)
                        # annotate the view on this new screenshot (under the output dir)
                        new_screenshot_path = self.output_dir + "critical_view_" + str(len(critical_event_ids)) + ".png"
                        print(new_screenshot_path)
                        from_state_of_critical_event.annotate_view_on_screenshot(
                            from_state_of_critical_event.screenshot_path,
                            new_screenshot_path,
                            [view_of_event],  # the matched view
                            (0, 0, 255)  # Color: Red
                        )

                        critical_event_info.append("event id: " + str(event_id) + ", screenshot:" + new_screenshot_path)

        return critical_event_ids, critical_event_info


if __name__ == '__main__':
    ap = ArgumentParser()

    ap.add_argument("--apk", action="store", dest="apk_path",
                    help="the apk path.")
    ap.add_argument("--output", action="store", dest="output_dir",
                    help="the testing output dir.")
    ap.add_argument("--cluster", action="store_true", dest="cluster_original_utg",
                    help="cluster the original utg, and output the clustered utg.")
    ap.add_argument("--check-seeds", action="store_true", dest="check_seed_tests",
                    help="check whether some seeds contain specific events or states; use with --views")
    ap.add_argument("--mutant", action="store", dest="mutant_dir",
                    help="the mutant test dir.")
    ap.add_argument('--seed', action="store", dest='seed_dir',
                    help='seed of mutant, default is parent of output_dir')
    ap.add_argument("--views", action="store", dest="views_json_file",
                    help="views of critical events that should be included in the expected mutants.")

    opts = ap.parse_args()

    if opts.apk_path is None:
        print("Please give an apk.")
        exit()

    if opts.output_dir is None:
        print("Please give output dir.")
        exit()

    debugger = DroidMutatorDebugger(
        apk_path=opts.apk_path,
        output_dir=opts.output_dir,
        mutant_dir=opts.mutant_dir,
        seed_dir=opts.seed_dir,
        views_json_file=opts.views_json_file
    )

    if opts.cluster_original_utg:
        debugger.cluster_original_utg()
    elif opts.check_seed_tests:
        debugger.check_seed_tests()
    else:
        debugger.draw()
