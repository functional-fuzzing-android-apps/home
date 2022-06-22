# This file processes the checking results of mutant tests. The main goal is to merge and reduce false positives.
import datetime
import json
import re
import sys
import os
from argparse import ArgumentParser
from multiprocessing.pool import ThreadPool
from time import strftime, sleep
from typing import List, Dict, Tuple

from pathlib import Path
import logging

from droidbot.app import App
from droidbot.device import Device
from droidbot.gui_test import CheckingResult, GUITestCase, TEST_TAG_SEED_TEST, TEST_TAG_DYNAMIC_TEST, \
    TEST_TAG_MUTANT_TEST


class OracleCheckingConfigScript(object):
    """
    Specify the configurations when do oracle checking.

    The script supports three types of ignored views:
        (1) ignore_view_dict, any GUI effect changes w.r.t this view should be ignored
        (2) ignore_view_diff, specific view diff should be ignored
        (3) ignore_view_order, the order of view's children will be ignored

    The script supports the view context backtrack level:
        (1)
    """

    script_grammar = {
        'activity_name': {

        }
    }

    IGNORE_VIEW_DICT = "ignore_view_dict"
    IGNORE_VIEW_DIFF = "ignore_view_diff"
    IGNORE_VIEW_ORDER = "ignore_view_order"

    def __init__(self, script_dict):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.script_dict = script_dict


class ResultAnalyzer(object):

    def __init__(self, output_dir, apk_path=None, config_file_path=None, seed_test_ids=None, number_of_cores=None,
                 do_skip=None, include_view_text=None):

        self.output_dir = output_dir

        # create a dummy device object
        self.device = Device(device_serial="emulator-5554", is_emulator=True, output_dir=self.output_dir)

        # create the app object
        self.app = None if apk_path is None else App(apk_path, output_dir=self.output_dir)

        self.random_input = None

        # id of a given seed test to check
        self.seed_test_ids = seed_test_ids

        # number of cores to use
        if number_of_cores is None:
            # by default, we only use 4 cores
            self.number_of_cores = 4
        else:
            self.number_of_cores = int(number_of_cores)

        self.do_skip = do_skip  # skip seeds or mutants?
        self.include_view_text = include_view_text

        self.oracle_checking_log_file_path = os.path.join(self.output_dir, 'oracle-checking-' + strftime(
            "%Y-%m%d-%H%M%-S") + ".log")
        self.merge_checking_log_file_path = os.path.join(self.output_dir, 'merge-checking-' + strftime(
            "%Y-%m%d-%H%M%-S") + ".log")

        self.oracle_checking_config_dict = None
        self.ignored_views: Dict[str, dict] = dict()
        self.ignored_pages: Dict[str, dict] = dict()
        self.ignored_view_children_order: Dict[str, dict] = dict()
        self.gui_page_types_info: Dict[str, List[Dict]] = dict()
        if config_file_path is not None:
            config_file = open(config_file_path, "r", encoding='utf-8')
            self.oracle_checking_config_dict = json.load(config_file)
            config_file.close()
            if "ignored_views" in self.oracle_checking_config_dict:
                self.ignored_views = self.oracle_checking_config_dict['ignored_views']
            if "ignored_pages" in self.oracle_checking_config_dict:
                self.ignored_pages = self.oracle_checking_config_dict['ignored_pages']
            if "ignored_view_children_order" in self.oracle_checking_config_dict:
                self.ignored_view_children_order = self.oracle_checking_config_dict['ignored_view_children_order']
            if "gui_pages" in self.oracle_checking_config_dict:
                self.gui_page_types_info = self.oracle_checking_config_dict['gui_pages']

        self.total_generated_mutants: int = 0
        self.total_mutants_with_checking_result = 0
        self.total_mutants_with_coverage = 0

        # how many mutants were reported with semantic errors
        self.total_number_of_mutants_reported_with_semantic_errors = 0
        # how many semantic error instances were merged
        self.total_number_of_merged_semantic_error_instances = 0
        # how many semantic error instances are unique
        self.total_number_of_remaining_semantic_error_instances = 0

        self.all_mutants: Dict[str, List[str]] = {}
        self.all_mutants_with_crash_error: Dict[str, List[Tuple[str, str]]] = {}
        self.all_mutants_with_semantic_error: Dict[str, List[str]] = {}

        # key: the seed test id
        # value: the info of unique semantic errors of all mutants generated from this seed test
        self.all_unique_semantic_error_instances: Dict[str, Dict] = {}

    def scan_seeds_and_mutants(self):

        if len(self.all_mutants) != 0:
            # make sure we only scan once
            return

        base = Path(self.output_dir)
        seeds = [i for i in base.glob('seed-tests/seed-test-*')]  # get all seed tests in absolute path

        for seed_dir in seeds:

            seed_test_dir = str(seed_dir)

            if len(self.seed_test_ids) != 0 and os.path.basename(seed_test_dir) not in self.seed_test_ids:
                # only check the given seed test if it is specified
                continue

            self.all_mutants[seed_test_dir] = []

            seed_base = Path(seed_test_dir)
            mutants = [i for i in seed_base.glob('mutant-*')]  # get all mutant tests of this seed test in absolute path

            for mutant_dir in mutants:
                mutant_test_dir = str(mutant_dir)
                self.all_mutants[seed_test_dir].append(mutant_test_dir)

    def count_execution_results(self):

        for seed_test_dir in self.all_mutants:

            mutants = self.all_mutants[seed_test_dir]

            for mutant_test_dir in mutants:

                self.total_generated_mutants += 1

                if os.path.exists(os.path.join(mutant_test_dir, "coverage.ec")):
                    self.total_mutants_with_coverage += 1

                checking_result_json_file_path = os.path.join(mutant_test_dir, "checking_result.json")
                if os.path.exists(checking_result_json_file_path):
                    self.total_mutants_with_checking_result += 1

                    try:
                        checking_result_json_file = open(checking_result_json_file_path, "r")
                        checking_result_dict = json.load(checking_result_json_file)
                        checking_result_json_file.close()

                        if checking_result_dict['crash_error']:
                            # collect the mutant if it has crash errors
                            if seed_test_dir not in self.all_mutants_with_crash_error:
                                self.all_mutants_with_crash_error[seed_test_dir] = \
                                    [(mutant_test_dir, checking_result_dict['insert_position'])]
                            else:
                                self.all_mutants_with_crash_error[seed_test_dir].append(
                                    (mutant_test_dir, checking_result_dict['insert_position']))

                        if checking_result_dict['semantic_error']:
                            # collect the mutant if it has semantic errors
                            if seed_test_dir not in self.all_mutants_with_semantic_error:
                                self.all_mutants_with_semantic_error[seed_test_dir] = [mutant_test_dir]
                            else:
                                self.all_mutants_with_semantic_error[seed_test_dir].append(mutant_test_dir)

                    except Exception:
                        print("mutant: %s's checking_result.json is corrupted, skip it!" % mutant_test_dir)
                        pass

    def do_oracle_checking_on_single_mutant(self, mutant_test_dir):
        """
        do oracle checking on single mutant
        :param mutant_test_dir:
        :return: None if the mutant test was not executed (thus we cannot do oracle checking now)
                or some exception happens.
        """

        # get the absolute path of the mutant test
        absolute_path_of_mutant_test = os.path.abspath(mutant_test_dir)
        if not os.path.exists(os.path.join(absolute_path_of_mutant_test, "events")):
            current_datetime = datetime.datetime.now()
            test_execution_result = "[" + str(current_datetime) + "]" \
                                    + "[this mutant was not executed, skip it]" "\n"
            print("\n\n" + test_execution_result + "\n\n")
            return None

        seed_test_dir = os.path.dirname(absolute_path_of_mutant_test)

        try:
            seed_test = GUITestCase(self.device, self.app, self.random_input,
                                    test_output_dir=seed_test_dir,
                                    test_tag=TEST_TAG_SEED_TEST).recover_test_case()

            mutant_test = GUITestCase(self.device, self.app, self.random_input,
                                      test_output_dir=mutant_test_dir,
                                      test_tag=TEST_TAG_MUTANT_TEST).recover_test_case()

            dynamic_mutant_test = GUITestCase(self.device, self.app, self.random_input,
                                              test_output_dir=mutant_test_dir,
                                              test_tag=TEST_TAG_DYNAMIC_TEST).recover_test_case()

            dynamic_mutant_test.merge_with_another_test(seed_test, output_utg=False)
            dynamic_mutant_test.merge_with_another_test(mutant_test, output_utg=False)

            # clean the oracle checking data
            dynamic_mutant_test.clean_mutant_data(clean_oracle_data=True)

            # BEGIN
            # Check whether this mutant is caused by imprecise/incomplete independent trace loop
            # Rule 1: if the seed test's gui page (right before the insertion position) is not comparable with
            #   the mutant test's gui page (the page right after the independent trace), then directly discard
            #   this mutant.
            # TODO temporarily disable this checking
            # from_state_before_insertion_position: DeviceState = dynamic_mutant_test.get_from_state_from_test_by_index(
            #     dynamic_mutant_test.insert_start_position)
            # from_state_after_independent_trace: DeviceState = dynamic_mutant_test.get_from_state_from_test_by_index(
            #     dynamic_mutant_test.insert_end_position)
            #
            # if from_state_before_insertion_position is None or from_state_after_independent_trace is None:
            #     # make sure this is a valid mutant (i.e., the independent trace was fully executed)
            #     return None
            #
            # page_type_1 = from_state_before_insertion_position.get_gui_page_type(self.gui_page_types_info)
            # page_type_2 = from_state_after_independent_trace.get_gui_page_type(self.gui_page_types_info)
            #
            # if page_type_1 != page_type_2:
            #     print("\n\t[%s contains imprecise/incomplete independent trace loop, prune it!!!]" %
            #           os.path.basename(mutant_test_dir))
            #     return None

            # END

            dynamic_mutant_test.do_oracle_checking(seed_test, gui_page_types_info=self.gui_page_types_info)

            current_datetime = datetime.datetime.now()
            test_execution_result = "[" + str(current_datetime) + "]" \
                                    + "seed test: " + str(seed_test.test_id) \
                                    + ", mutant test: " + str(dynamic_mutant_test.test_id) \
                                    + ", has crash?: " + str(dynamic_mutant_test.has_crash) \
                                    + ", has semantic error?: " + str(dynamic_mutant_test.has_semantic_error) + "\n"

            print("\n\n" + test_execution_result + "\n\n")

            return mutant_test_dir

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(e)

            return None

    def do_oracle_checking_for_one_seed_test(self, seed_test_dir):

        mutants_list = self.all_mutants[seed_test_dir]

        # split the mutant list
        mutants_cnt = len(mutants_list)
        split_size = self.number_of_cores * 10
        split_mutants_list: List[List[str]] = [mutants_list[i:i + split_size] for i in
                                               range(0, len(mutants_list), split_size)]
        processed_mutants_cnt = 0

        for sublist_of_mutants in split_mutants_list:

            thread_results = []
            n = self.number_of_cores

            # run these mutants
            p = ThreadPool(n)
            for mutant_test_dir in sublist_of_mutants:
                result = p.apply_async(self.do_oracle_checking_on_single_mutant, args=(mutant_test_dir,))
                thread_results.append(result)
            p.close()
            p.join()

            processed_mutants_cnt += len(thread_results)
            print("\n\t[processed %d/%d mutants of %s]\n" % (
                processed_mutants_cnt, mutants_cnt, os.path.basename(seed_test_dir)))

            log_file = open(self.oracle_checking_log_file_path, "a+")
            output_str = ""
            for index in range(0, len(thread_results)):
                r = thread_results[index].get()
                if r:
                    # oracle checking successfully finished on this mutant
                    output_str += r + '\n'
            log_file.write(output_str)
            log_file.close()

    def skip_mutants(self):

        # read mutants to skip
        base = Path(self.output_dir)
        mutants_to_skip_dict = {}
        for log_file in base.glob('oracle-checking-*.log'):
            for mutant_test_dir in log_file.read_text().strip().split('\n'):
                print("skip oracle checking for the mutant: %s" % mutant_test_dir)
                seed_test_dir = os.path.dirname(os.path.abspath(mutant_test_dir))
                if seed_test_dir not in mutants_to_skip_dict:
                    mutants_to_skip_dict[seed_test_dir] = [mutant_test_dir]
                else:
                    mutants_to_skip_dict[seed_test_dir].append(mutant_test_dir)

        skipped_mutant_cnt = 0
        # skip mutants
        for seed_test_dir in self.all_mutants:
            if seed_test_dir in mutants_to_skip_dict:
                mutants_to_skip = mutants_to_skip_dict[seed_test_dir]
                remaining_mutants = list(set(self.all_mutants[seed_test_dir]) - set(mutants_to_skip))
                skipped_mutant_cnt += len(mutants_to_skip)
                self.all_mutants[seed_test_dir] = remaining_mutants

        print("skipped %d mutants in total." % skipped_mutant_cnt)
        sleep(5)

    def do_oracle_checking(self):

        self.scan_seeds_and_mutants()

        if self.do_skip:
            self.skip_mutants()

        for seed_test_dir in self.all_mutants:
            self.do_oracle_checking_for_one_seed_test(seed_test_dir)

    def merge_reported_errors_in_single_mutant(self, mutant_test_dir):

        mutant_test_output_dir = str(mutant_test_dir)

        checking_result_json_file_path = os.path.join(mutant_test_output_dir, "checking_result.json")
        first_error_instance_index_file_path = os.path.join(mutant_test_output_dir, "utg_1.json")

        if not os.path.exists(checking_result_json_file_path) or not os.path.exists(
                first_error_instance_index_file_path):
            # do not check the mutants if no checking result and error instance files
            return None

        checking_result_json_file = open(checking_result_json_file_path, "r", encoding='utf-8')
        checking_result_dict = json.load(checking_result_json_file)

        checking_result_obj = CheckingResult.from_dict(checking_result_dict, mutant_test_output_dir, self.device)

        unique_error_instances, pruned_error_instances = \
            checking_result_obj.compute_unique_errors(self.ignored_views, self.ignored_pages,
                                                      self.ignored_view_children_order,
                                                      self.gui_page_types_info,
                                                      include_view_text=self.include_view_text)

        is_faithfully_replayed = checking_result_obj.is_faithfully_replayed

        print("\n=== Result ===")
        print("unique error instances: %d" % len(unique_error_instances))
        print("pruned error instances: %d" % len(pruned_error_instances))

        return unique_error_instances, is_faithfully_replayed, pruned_error_instances

    def merge_reported_errors_for_one_seed_test(self, seed_test_dir):

        mutants_list: List[str] = self.all_mutants_with_semantic_error[seed_test_dir]

        # key: a tuple that contains the error strs of seed test and its mutant test, respectively
        # value: a list of mutant_batch_id (corresponding to an error instances) with the execution status
        #   of the mutant (these error instances have the same tuple of error strs)
        unique_semantic_error_instances_of_one_seed: Dict[Tuple[str, str], List[Tuple[str, bool]]] = dict()

        # set_of_unique_error_str_of_one_seed_test: Set[int] = set()

        mutants_cnt = len(mutants_list)
        split_size = self.number_of_cores * 10
        split_mutants_list: List[List[str]] = [mutants_list[i:i + split_size] for i in
                                               range(0, len(mutants_list), split_size)]
        processed_mutants_cnt = 0

        for sublist_of_mutants in split_mutants_list:

            thread_results = []
            n = self.number_of_cores

            p = ThreadPool(n)
            for mutant_test_dir in sublist_of_mutants:
                result = p.apply_async(self.merge_reported_errors_in_single_mutant, args=(mutant_test_dir,))
                thread_results.append(result)
            p.close()
            p.join()

            processed_mutants_cnt += len(thread_results)
            print("\n\t[processed %d/%d mutants of %s]\n" % (
                processed_mutants_cnt, mutants_cnt, os.path.basename(seed_test_dir)))

            for index in range(0, len(thread_results)):

                # get the thread result
                unique_error_instances, is_faithfully_replayed, pruned_error_instances = thread_results[index].get()

                if len(unique_error_instances) != 0:
                    self.total_number_of_mutants_reported_with_semantic_errors += 1

                # add the pruned semantic errors instances from one single mutant
                self.total_number_of_merged_semantic_error_instances += len(pruned_error_instances)

                for mutant_batch_id in unique_error_instances:
                    error_str_tuple = unique_error_instances[mutant_batch_id]
                    if error_str_tuple not in unique_semantic_error_instances_of_one_seed:
                        unique_semantic_error_instances_of_one_seed[error_str_tuple] = [
                            (mutant_batch_id, is_faithfully_replayed)]
                    else:
                        unique_semantic_error_instances_of_one_seed[error_str_tuple].append(
                            (mutant_batch_id, is_faithfully_replayed))

                        duplicate_error_instance = unique_semantic_error_instances_of_one_seed[error_str_tuple][0][0]

                        # add the pruned semantic errors instances from other mutants (generated by one seed test)
                        self.total_number_of_merged_semantic_error_instances += 1
                        print("\n%s was pruned across mutants, duplicate with -> %s" % (
                            mutant_batch_id, duplicate_error_instance))

        self.all_unique_semantic_error_instances[seed_test_dir] = unique_semantic_error_instances_of_one_seed
        self.total_number_of_remaining_semantic_error_instances += len(unique_semantic_error_instances_of_one_seed)

        # log the seed when merging checking results finishes
        log_file = open(self.merge_checking_log_file_path, "a+")
        log_file.write(seed_test_dir + '\n')
        log_file.close()

    def skip_seeds(self):

        # read seeds to skip
        base = Path(self.output_dir)
        seeds_to_skip_list = []
        for log_file in base.glob('merge-checking-*.log'):
            for seed_test_dir in log_file.read_text().strip().split('\n'):
                seeds_to_skip_list.append(seed_test_dir)

        # skip seeds
        filtered_dict = {}
        for seed_test_dir in self.all_mutants_with_semantic_error:
            if seed_test_dir not in seeds_to_skip_list:
                filtered_dict[seed_test_dir] = self.all_mutants_with_semantic_error[seed_test_dir]
            else:
                print("skip the seed test: %s" % seed_test_dir)
                sleep(2)

        self.all_mutants_with_semantic_error = filtered_dict

    def merge_reported_errors(self):

        self.scan_seeds_and_mutants()
        self.count_execution_results()

        if self.do_skip:
            self.skip_seeds()

        print("--- merge and reduce semantic errors ---")

        seeds_str = ""
        for seed_test_dir in self.all_mutants_with_semantic_error:
            self.merge_reported_errors_for_one_seed_test(seed_test_dir)
            seed_name = os.path.basename(seed_test_dir)  # e.g., 'seed-test-1'
            short_seed_name = 's' + str(seed_name).split('-')[2]  # e.g., 's1'
            seeds_str += short_seed_name + ","  # e.g., 's1,s2,'
            # dump the checking results when one seed is finished
            self.output_results(seeds_str)

    def do_oracle_checking_and_merge_checking_results(self):

        self.scan_seeds_and_mutants()
        self.count_execution_results()

        for seed_test_dir in self.all_mutants:
            self.do_oracle_checking_for_one_seed_test(seed_test_dir)
            self.merge_reported_errors_for_one_seed_test(seed_test_dir)
            self.output_results(os.path.basename(seed_test_dir))

    def output_results(self, seeds_str):

        # output the merged results
        output_str = ""

        # generated mutants and executed mutants
        output_str += "***Result Summary***\n\n"
        output_str += "#Total generated mutants, " + str(self.total_generated_mutants) + "\n"
        output_str += "#Executed mutants (w/ coverage results - coverage.ec), " + str(
            self.total_mutants_with_coverage) + "\n"
        output_str += "#Analyzed mutants (w/ oracle checking results - checking_result.json, " + str(
            self.total_mutants_with_checking_result) + "\n\n"
        print(output_str)

        # Crash Errors
        output_str += "***Crash Errors***\n\n"
        tmp_output_str = "[Seed Test Id], [Occurrences], [Mutant Test Id], [Execution Status], " \
                         "[Insert Position], [Error Instance], [True Positive] \n\n"
        total_number_of_mutants_with_crash_errors = 0
        for seed_test_dir in self.all_mutants_with_crash_error:
            mutant_info_list = self.all_mutants_with_crash_error[seed_test_dir]
            for mutant_info_tuple in mutant_info_list:
                mutant_test_dir, insert_position = mutant_info_tuple
                tmp_output_str += os.path.basename(seed_test_dir) + "," + "," + os.path.basename(mutant_test_dir) + \
                                  "," + "," + "insert_position_" + str(insert_position) + "," + "\n"
                total_number_of_mutants_with_crash_errors += 1
        output_str += tmp_output_str + "\n\n"
        print("[Crash Errors: %d]\n\n" % total_number_of_mutants_with_crash_errors)

        # Semantic Errors
        output_str += "***Semantic Errors***\n"
        total_number_of_mutants_with_semantic_errors = 0

        tmp_output_str = "[Seed Test Id], [1-Occurrence-mutants], [Occurrences], [Mutant Test Id], [Execution Status], " \
                         "[Insert Position], [Error Instance], [True Positive] \n\n"

        total_number_of_mutants_with_once_occurrence_semantic_errors_of_all_seed_tests = 0

        for seed_test_dir in self.all_unique_semantic_error_instances:

            print("ranking the semantic errors from %s" % seed_test_dir)
            total_number_of_mutants_with_one_occurrence_semantic_errors_of_one_seed_test = 0

            unique_semantic_error_instances_of_one_seed = self.all_unique_semantic_error_instances[seed_test_dir]

            # sort by the occurrences of error str from the least to the most
            error_instances_list = []
            for error_str_tuple in unique_semantic_error_instances_of_one_seed:
                error_instances_list.append(unique_semantic_error_instances_of_one_seed[error_str_tuple])
            error_instances_list = sorted(error_instances_list, key=lambda x: len(x))

            # key: the occurrence and the mutant id
            # value: the error instances of this mutant
            unique_mutants_with_semantic_errors_of_one_seed_test: Dict[
                Tuple[str, str, bool], List[Tuple[str, str]]] = dict()

            # get the seed test id
            seed_test_id = os.path.basename(seed_test_dir)

            for tmp_list_x in error_instances_list:

                occurrences: str = str(len(tmp_list_x))
                mutant_info: List[str] = tmp_list_x[0][0].split('/')
                mutant_execution_status: bool = tmp_list_x[0][1]

                mutant_test_id_re = re.compile('mutant-*')
                mutant_test_id = list(filter(mutant_test_id_re.match, mutant_info))[0]
                insertion_position_re = re.compile('insert_position_*')
                insert_position = list(filter(insertion_position_re.match, mutant_info))[0]
                error_instance_re = re.compile('index_aligned_*')
                error_instance = list(filter(error_instance_re.match, mutant_info))[0]

                if (occurrences, mutant_test_id, mutant_execution_status) not in \
                        unique_mutants_with_semantic_errors_of_one_seed_test:

                    unique_mutants_with_semantic_errors_of_one_seed_test[
                        (occurrences, mutant_test_id, mutant_execution_status)] = [(insert_position, error_instance)]
                else:
                    unique_mutants_with_semantic_errors_of_one_seed_test[
                        (occurrences, mutant_test_id, mutant_execution_status)].append(
                        (insert_position, error_instance))

                print("occurrence: %d, one mutant_batch_id: %s" % (len(tmp_list_x), tmp_list_x[0]))

            # assemble the output content
            tmp_output_str += seed_test_id
            tmp_output_mutant_str = ""

            for mutant_test_info in unique_mutants_with_semantic_errors_of_one_seed_test:

                total_number_of_mutants_with_semantic_errors += 1

                occurrences, mutant_test_id, mutant_execution_status = mutant_test_info
                exec_status = "faithful" if mutant_execution_status else "not-faithful"
                tmp_output_mutant_str += "," + "," + occurrences + "," + mutant_test_id + "," + exec_status

                if int(occurrences) == 1:
                    total_number_of_mutants_with_one_occurrence_semantic_errors_of_one_seed_test += 1

                error_instances_list = unique_mutants_with_semantic_errors_of_one_seed_test[mutant_test_info]

                for i in range(0, len(error_instances_list)):
                    insert_position, error_instance = error_instances_list[i]
                    if i == 0:
                        tmp_output_mutant_str += "," + insert_position + "," + error_instance + "\n"
                    else:
                        tmp_output_mutant_str += "," + "," + "," + "," + "," + insert_position + "," + error_instance + "\n"
                tmp_output_mutant_str += "\n"

            tmp_output_str += "[" + str(total_number_of_mutants_with_one_occurrence_semantic_errors_of_one_seed_test) \
                              + "]" + tmp_output_mutant_str

            total_number_of_mutants_with_once_occurrence_semantic_errors_of_all_seed_tests += \
                total_number_of_mutants_with_one_occurrence_semantic_errors_of_one_seed_test

        output_str += "#mutants reported w/ semantic errors, %d, \n#pruned semantic error instances, %d\n" % \
                      (self.total_number_of_mutants_reported_with_semantic_errors,
                       self.total_number_of_merged_semantic_error_instances)
        output_str += "#remaining mutants w/ semantic errors, %d, \n#remaining error instances, %d, \n" \
                      "#remaining mutants w/ one-occurrence semantic errors, %d\n\n" % \
                      (total_number_of_mutants_with_semantic_errors,
                       self.total_number_of_remaining_semantic_error_instances,
                       total_number_of_mutants_with_once_occurrence_semantic_errors_of_all_seed_tests)
        print("#mutants reported w/ semantic errors, %d, \n#pruned semantic error instances, %d\n" %
              (self.total_number_of_mutants_reported_with_semantic_errors,
               self.total_number_of_merged_semantic_error_instances))
        print("#remaining mutants w/ semantic errors, %d, \n#remaining error instances, %d, \n"
              "#remaining mutants w/ one-occurrence semantic errors, %d\n\n" %
              (total_number_of_mutants_with_semantic_errors,
               self.total_number_of_remaining_semantic_error_instances,
               total_number_of_mutants_with_once_occurrence_semantic_errors_of_all_seed_tests))
        output_str += "\n\n" + tmp_output_str + "\n"

        # the final result locates under main_output_dir/merged_results.csv
        from time import strftime
        postprocess_result_file_path = os.path.join(self.output_dir,
                                                    "merged_results_" + strftime("%Y-%m%d-%H%M%-S") +
                                                    "_" + seeds_str +
                                                    ".csv")
        postprocess_result_file = open(postprocess_result_file_path, "w")
        postprocess_result_file.write(output_str)
        postprocess_result_file.close()
        print("Final result file: %s" % postprocess_result_file_path)


if __name__ == '__main__':

    ap = ArgumentParser()

    ap.add_argument("-o", action="store", dest="output_dir",
                    help="the testing output dir.")
    ap.add_argument("-f", action="store", dest="config_file",
                    help="the oracle checking configuration file.")
    ap.add_argument("--apk", action="store", dest="app_apk",
                    help="the app apk file.")
    ap.add_argument("--do-oracle-checking", action="store_true", dest="do_oracle_checking", default=False,
                    help="do the oracle checking")
    ap.add_argument("--merge-checking-results", action="store_true", dest="merge_checking_results", default=False,
                    help="merge the oracle checking results")
    ap.add_argument("--check-and-merge", action="store_true", dest="check_and_merge", default=False,
                    help="do oracle checking and merge checking results iteratively for each seed test")
    ap.add_argument("--mutant", action="store", dest="mutant_test_dir",
                    help="the specific mutant to do oracle checking")
    ap.add_argument("--seeds", action="store", dest="seed_test_ids",
                    help="the specific seed test id, e.g., \"1;2;3\" to do oracle checking and merging checking results")
    ap.add_argument('--no-view-text', dest='include_view_text', default=True,
                    action='store_false',
                    help='Do *NOT* include view text when merging error reports')
    ap.add_argument("--cores", action="store", dest="num_of_cores",
                    help="specify the number of cores to use, please mind average load")
    ap.add_argument('--skip', dest='do_skip', default=False,
                    action='store_false',
                    help='Do skip mutants or seeds which have finished oracle checking or merging checking results '
                         'based on all `<-o>/oracle-checking-<time>.log`or `<-o>/merge-checking-<time>.log`')

    opts = ap.parse_args()

    if opts.config_file is not None and not os.path.exists(opts.config_file):
        print("cannot find the config file")
        sys.exit(0)

    ids = set()
    if opts.seed_test_ids is not None:
        for i in opts.seed_test_ids.strip(';').split(';'):
            ids.add('seed-test-{}'.format(int(i)))
        print("handling seed test: %s" % ids)

    result_analyzer = ResultAnalyzer(opts.output_dir, opts.app_apk, opts.config_file,
                                     seed_test_ids=ids,
                                     number_of_cores=opts.num_of_cores,
                                     do_skip=opts.do_skip,
                                     include_view_text=opts.include_view_text)

    if opts.do_oracle_checking:
        if opts.mutant_test_dir is not None:
            result_analyzer.do_oracle_checking_on_single_mutant(opts.mutant_test_dir)
        else:
            result_analyzer.do_oracle_checking()

    if opts.merge_checking_results:
        if opts.mutant_test_dir is not None:
            result_analyzer.merge_reported_errors_in_single_mutant(opts.mutant_test_dir)
        else:
            result_analyzer.merge_reported_errors()

    if opts.check_and_merge:
        result_analyzer.do_oracle_checking_and_merge_checking_results()
