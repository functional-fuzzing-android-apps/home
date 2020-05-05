import logging
import json
import os
import random
import datetime
from shutil import copyfile
from typing import List, Dict

import networkx as nx

from .utils import list_to_html_table, replace_file
from .input_event import InputEvent
from .device_state import COLOR_RED, DeviceState


class UTG(object):
    """
    UI transition graph
    """

    def __init__(self, device, app, random_input):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.device = device
        self.app = app
        self.random_input = random_input

        #  some notes on the storage structure of self.G
        # self.G.nodes(): get the nodes of UTG, each node is represented/stored as a state.state_str (type of string),
        #   and each state (type of DeviceState) is stored in its node property "state".
        #   E.g., self.G.add_node(state.state_str, state=state)
        #         self.G.nodes[from_state_str]["state"]
        # self.G.edges(): get the edges of UTG, each edge is represented/stored as a pair of state.state_str,
        #   E.g., (old_state.state_str, new_state.state_str)
        #   and each event is stored in the edge property "events"
        #   E.g., self.G.add_edge(old_state.state_str, new_state.state_str, events={})
        #   For each event, it is stored as a dict, in which the key is event_str (type of string), and the value
        #   is another dict, in the form of
        #       {event_str: {"event": event (type of InputEvent), "id": event_id (type of Int)}}
        #   E.g., self.G[old_state.state_str][new_state.state_str]["events"][event_str] = {
        #             "event": event,
        #             "id": self.effective_event_count
        #         }
        #         event_str in self.G[old_state.state_str][new_state_str]["events"]
        self.G = nx.DiGraph()

        self.effective_event_strs = set()
        self.ineffective_event_strs = set()
        self.explored_state_strs = set()
        self.reached_state_strs = set()
        self.reached_activities = set()

        self.first_state_str = None
        self.last_state_str = None
        self.last_state = None
        self.last_transition = None
        self.effective_event_count = 0
        self.input_event_count = 0

        self.start_time = datetime.datetime.now()

    def get_node_by_state_str(self, state_str):
        return self.G.nodes[state_str]["state"]

    #  update the execution info
    def record_execution_path(self, event, event_type, old_state, new_state):
        if not old_state or not new_state or not event or not event_type:
            return

        if event.__class__.__name__.startswith("RestartEvent") or \
                event.__class__.__name__.startswith("NOPEvent"):
            return
        #  update new state's path events by old state's path events
        # the path event can be viewed as "path constraint"
        # We do not need to update the path events if the app was fresh restarted
        new_state.update_path_events(old_state, event)
        # update state type
        new_state.update_state_type(event_type)
        #  debug info
        new_state.log_execution_path_events_info()

    #  the key method that constructs the utg
    def add_transition(self, event, old_state, new_state, event_log_file_path=None, event_views_file_path=None,
                       remove_self_loop_transition=True):
        self.add_node(old_state)
        self.add_node(new_state)

        # make sure the states are not None
        if not old_state or not new_state:
            return

        event_str = event.get_event_str(old_state)
        self.input_event_count += 1

        #  handle self-loop in the utg
        if old_state.state_str == new_state.state_str and remove_self_loop_transition:
            self.ineffective_event_strs.add(event_str)
            # delete the transitions including the event from utg
            for new_state_str in self.G[old_state.state_str]:
                if event_str in self.G[old_state.state_str][new_state_str]["events"]:
                    self.G[old_state.state_str][new_state_str]["events"].pop(event_str)
            if event_str in self.effective_event_strs:
                self.effective_event_strs.remove(event_str)
            return

        self.effective_event_strs.add(event_str)
        self.effective_event_count += 1

        if (old_state.state_str, new_state.state_str) not in self.G.edges():
            self.G.add_edge(old_state.state_str, new_state.state_str, events={})

        self.G[old_state.state_str][new_state.state_str]["events"][event_str] = {
            "event": event,
            "id": self.effective_event_count,
            "event_log_file_path": event_log_file_path,
            "event_views_file_path": event_views_file_path if event_views_file_path is not None else []
        }
        # print("in utg, old_state_str: %s" % old_state.state_str)
        # print("event_str: %s" % event_str)
        # print(event)
        # view_images = ["views/view_" + view["view_str"] + ".png"
        #                for view in event.get_views()]
        # print(view_images)
        # print("in utg, new_state_str: %s" % new_state.state_str)

        self.last_state = new_state
        self.last_state_str = new_state.state_str
        self.last_transition = (old_state.state_str, new_state.state_str)
        self.__output_utg()

    def add_node(self, state):
        if not state:
            return
        if state.state_str not in self.G.nodes():
            # Note: this statement has been moved after calling get_current_state()
            # state.save2dir()
            self.G.add_node(state.state_str, state=state)
            if self.first_state_str is None:
                self.first_state_str = state.state_str
        if state.foreground_activity.startswith(self.app.package_name):
            self.reached_activities.add(state.foreground_activity)

    def load_event_from_event_log_file(self, event_log_file_path):

        with open(event_log_file_path, "r") as f:
            try:
                # event_log_dict is in the form of EventLog
                event_log_dict = json.load(f)
            except Exception as e:
                self.logger.info("Loading %s failed when recovering the original utg: %s" %
                                 (event_log_file_path, e))
            event = InputEvent.from_dict(event_log_dict['event'])
        return event

    def recover_original_utg(self, utg_dir, recovered_utg_tmp_file_name="utg_recovery"):
        """
        Recover the original utg according to the files under "events/", "states/" and "utg.json"
            "events/" stores all the executed events;
            "states/" stores all the witnessed states;
            "utg.json" stores the utg, which includes the utg nodes (ie, states) and edges (ie, events)
        :param utg_dir: the directory where "utg.json" locates in.
        :param recovered_utg_tmp_file_name
        :return: utg
        """

        import os
        # get utg nodes and edges from "utg.json"
        utg_json_file_path = os.path.join(utg_dir, "utg.json")
        assert (
            os.path.exists(utg_json_file_path)
        ), 'Cannot find the utg file, please check whether you have already constructed the utg?'
        utg_json_file = open(utg_json_file_path, "r")
        utg_data = json.load(utg_json_file)
        # close the utg json file
        utg_json_file.close()
        utg_nodes = utg_data['nodes']  # get the utg nodes
        utg_edges = utg_data['edges']  # get the utg edges

        # Fix: the original utg internally uses 'num_effective_events' to assign utg event id
        # We should start the numbering of new event ids from 'num_input_events' rather than 'num_effective_events'.
        #   This avoids duplicate event ids in the utg
        utg_num_input_events = utg_data['num_input_events']  # get the number of input events

        # the set of utg states in the form of the dict {state_str: DeviceState}
        utg_states = {}
        for node in utg_nodes:
            # recover the device state
            state_json_file_path = os.path.join(utg_dir, node['state'])
            state = self.device.recover_device_state(state_json_file_path,
                                                     screenshot_path=os.path.join(utg_dir, node['image']),
                                                     first_state=("<FIRST>" in node['label']),
                                                     last_state=("<LAST>" in node['label']))
            utg_states[state.state_str] = state

        # the set of utg transitions in the form of dict {edge_id: Edge}
        #   Here, edge['id'] is in the form of "from_state.state_str-->to_state.state_str"
        utg_transitions = {}
        for edge in utg_edges:
            utg_transitions[edge['id']] = edge

        output_dir = self.device.output_dir

        for utg_transition_dict in utg_transitions.values():
            utg_transition_events = utg_transition_dict['events']
            for utg_transition_event_dict in utg_transition_events:
                event_log_file_path = os.path.join(output_dir, utg_transition_event_dict['event_log_file_path'])
                assert (
                        event_log_file_path is not None
                ), "event_log_file_path cannot be None!"

                # get event
                event = self.load_event_from_event_log_file(event_log_file_path)
                assert (
                        event is not None
                ), "Load event from event log file failed when recovering the original utg!"

                event_views_file_path = [os.path.join(output_dir, event_view_file_path)
                                         for event_view_file_path in
                                         utg_transition_event_dict['view_images']]
                event_str = utg_transition_event_dict['event_str']
                event_id = utg_transition_event_dict['event_id']

                # get the from_state and to_state
                from_state = utg_states[utg_transition_dict['from']]
                to_state = utg_states[utg_transition_dict['to']]

                self.__add_transition_for_recovering_utg(event, event_id, event_str,
                                                         event_log_file_path,
                                                         event_views_file_path,
                                                         from_state, to_state)

        # update fields, make sure we will not have duplicate utg event ids in the original utg
        self.input_event_count = utg_num_input_events
        self.effective_event_count = utg_num_input_events

        # TODO only for debugging: output the recovered original utg
        self.output_utg_for_debug(output_dir,
                                  js_file=recovered_utg_tmp_file_name + ".js",
                                  json_file=recovered_utg_tmp_file_name + ".json")

    #
    def __add_transition_for_recovering_utg(self, input_event,
                                            utg_id_of_input_event,
                                            event_str_of_input_event,
                                            event_log_file_path,
                                            event_views_file_path,
                                            old_state, new_state):

        self.__add_node_for_recovering_utg(old_state)
        self.__add_node_for_recovering_utg(new_state)

        # make sure the states are not None
        if not old_state or not new_state:
            return

        event_str = event_str_of_input_event

        #  handle self-loop in the utg
        # if old_state.state_str == new_state.state_str:
        #     self.ineffective_event_strs.add(event_str)
        #     # delete the transitions including the event from utg
        #     for new_state_str in self.G[old_state.state_str]:
        #         if event_str in self.G[old_state.state_str][new_state_str]["events"]:
        #             self.G[old_state.state_str][new_state_str]["events"].pop(event_str)
        #     if event_str in self.effective_event_strs:
        #         self.effective_event_strs.remove(event_str)
        #     return

        self.effective_event_strs.add(event_str)

        if (old_state.state_str, new_state.state_str) not in self.G.edges():
            self.G.add_edge(old_state.state_str, new_state.state_str, events={})

        self.G[old_state.state_str][new_state.state_str]["events"][event_str] = {
            "event": input_event,
            "id": utg_id_of_input_event,
            "event_log_file_path": event_log_file_path,
            "event_views_file_path": event_views_file_path
        }

    #
    def __add_node_for_recovering_utg(self, state):
        """
        recover utg
        :param state:
        :return:
        """
        if not state:
            return
        if state.state_str not in self.G.nodes():
            self.G.add_node(state.state_str, state=state)
            if state.first_state:
                self.first_state_str = state.state_str
            if state.last_state:
                self.last_state_str = state.state_str
        if state.foreground_activity.startswith(self.app.package_name):
            self.reached_activities.add(state.foreground_activity)

    ##########################
    #   clustered utg
    ##########################

    def cluster_utg_structure(self, original_utg, output_clustered_utg=False, clustered_utg_file_name="utg_cluster"):
        """
        Cluster the utg.
        We use state.structure_str to uniquely represent a utg node, and thus if two nodes have the same
            state.structure_str, they will be merged into one node (Currently, only the first such node will be stored,
            and all the remaining similar ones will be discarded).
        As for utg edges, we use event_structure_str (which is composed of from_state.structure_str and view_str)
            to uniquely represent a utg edge (i.e., event). Note view_str is still computed with from_state.state_str
            rather than from_state.structure_str

        Note that the clustered utg reuses the utg event ids from the original utg !!

        :param original_utg: the original utg
        :param output_clustered_utg:
        :param clustered_utg_file_name: the clustered utg file name
        """
        for state_transition in original_utg.G.edges():
            # get the state_str
            from_state_str = state_transition[0]
            to_state_str = state_transition[1]

            # get the state
            from_state = original_utg.G.nodes[from_state_str]["state"]
            to_state = original_utg.G.nodes[to_state_str]["state"]

            # get the events between from_state and to_state
            events = original_utg.G[from_state_str][to_state_str]["events"]

            event_list = []
            for event_str, event_info in sorted(iter(events.items()), key=lambda x: x[1]["id"]):
                # Note: event_structure_str is generated by using state.structure_str rather than state.state_str
                event_structure_str = event_info["event"].get_event_str(from_state, content_free=True)
                event_list.append({
                    "event_str": event_structure_str,
                    "event_id": event_info["id"],
                    "event": event_info["event"],
                    "event_log_file_path": event_info['event_log_file_path'],
                    "event_views_file_path": event_info["event_views_file_path"]
                })

            for event_dict in event_list:
                self.__add_transition_for_clustering_utg(event_dict, from_state, to_state)

        # output the clustered utg (cluster_utg.js) and index_cluster.html
        if output_clustered_utg:
            output_dir = self.device.output_dir
            self.output_utg_for_debug(output_dir,
                                      clustered_utg_file_name + ".js",
                                      clustered_utg_file_name + ".json")

            original_html_file_path = os.path.join(output_dir, "index.html")
            new_html_file_path = os.path.join(output_dir, "index_cluster.html")

            if os.path.exists(original_html_file_path):
                copyfile(original_html_file_path, new_html_file_path)
                replace_file(new_html_file_path, lambda s: s.replace('utg.js',
                                                                     clustered_utg_file_name + '.js'))

    def __add_transition_for_clustering_utg(self, event_dict, old_state, new_state):

        self.__add_node_for_clustering_utg(old_state)
        self.__add_node_for_clustering_utg(new_state)

        # make sure the states are not None
        if not old_state or not new_state:
            return

        event_str = event_dict["event_str"]
        event_id = event_dict["event_id"]
        event = event_dict["event"]
        event_log_file_path = event_dict['event_log_file_path']
        event_views_file_path = event_dict["event_views_file_path"]

        #  handle self-loop in the utg
        # if old_state.structure_str == new_state.structure_str:
        #     for new_state_structure_str in self.G[old_state.structure_str]:
        #         if event_str in self.G[old_state.structure_str][new_state_structure_str]["events"]:
        #             self.G[old_state.structure_str][new_state_structure_str]["events"].pop(event_str)
        #     return

        if (old_state.structure_str, new_state.structure_str) not in self.G.edges():
            self.G.add_edge(old_state.structure_str, new_state.structure_str, events={})

        # count the number of effective events before adding
        # if event_str not in self.G[old_state.structure_str][new_state.structure_str]["events"]:
        #     self.effective_event_count += 1

        # Optimization: remove similar events on one transition
        #   We assume: if two events (1) are of same event type,
        #                            (2) have same view property,
        #   Then, these two events are same. We can safely reduce the complexity of the cluster model
        for tmp_event_str in self.G[old_state.structure_str][new_state.structure_str]["events"]:
            tmp_event_dict = self.G[old_state.structure_str][new_state.structure_str]["events"][tmp_event_str]
            tmp_event = tmp_event_dict["event"]
            if DeviceState.equal_input_events(tmp_event, event):
                return

        self.effective_event_count += 1

        self.G[old_state.structure_str][new_state.structure_str]["events"][event_str] = {
            "event": event,
            "id": event_id,
            "event_log_file_path": event_log_file_path,
            "event_views_file_path": event_views_file_path,
            # the concrete state (not the clustered state) that the event belongs to
            "original_utg_from_state_str": old_state.state_str,
            "original_utg_to_state_str": new_state.state_str
        }

    def __add_node_for_clustering_utg(self, state):
        if not state:
            return
        # for cluster utg, we use state.structure_str
        if state.structure_str not in self.G.nodes():
            self.G.add_node(state.structure_str, state=state)
            if state.first_state:
                self.first_state_str = state.structure_str
            if state.last_state:
                self.last_state_str = state.structure_str
        if state.foreground_activity.startswith(self.app.package_name):
            self.reached_activities.add(state.foreground_activity)

    ###################################

    #
    def add_utg_transition_for_gui_test(self, event, old_state, new_state, utg_output_dir, gui_test_tag,
                                        event_id=None,
                                        event_str=None,
                                        event_color=None,
                                        is_inserted_event=False,
                                        event_log_file_path=None,
                                        event_views_file_path=None,
                                        insert_start_position=None,
                                        independent_trace_len=None,
                                        utg_event_ids_of_test=None,
                                        output_utg=True,
                                        remove_self_loop_transition=False):
        """
        Construct the utg for a gui test case by adding utg transitions.

        Some note:
        To facilitate manual checking, we put the utgs of seed test, mutant test, and dynamic test into the same
          big utg. In this way, we can view three test formats in one html.
        The key is ensure these utg standalone (do not mess up with each other). To achieve this, we use
          "state_str + test_tag" as the state signature in UTG.
        Note state_str of original states will be kept unaffected. Only the outputted utg file will contain
          "state_str + test_tag" as the "state_str" for each state.

        :param event:   the event of the transition to be added
        :param event_id:
        :param event_str:
        :param old_state:   the from_state of the event
        :param new_state:   the to_state of the event
        :param utg_output_dir:  the output dir of this utg
        :param gui_test_tag:    the tag of the gui test
        :param event_color:     the color for annotation
        :param is_inserted_event:
        :param event_log_file_path:
        :param event_views_file_path:
        :param insert_start_position:
        :param independent_trace_len:
        :param utg_event_ids_of_test:
        :param output_utg:
        :param remove_self_loop_transition:
        :return:
        """

        self.add_utg_node_for_gui_test(old_state, gui_test_tag)
        self.add_utg_node_for_gui_test(new_state, gui_test_tag)

        if old_state is None or new_state is None:
            # will not add transitions if old_state or new_state is None
            return

        old_state_str = old_state.state_str + gui_test_tag
        new_state_str = new_state.state_str + gui_test_tag

        _event = event
        _event_str = event_str if event_str is not None else event.get_event_str(old_state)
        if event_id is not None:
            _event_id = event_id
        else:
            self.input_event_count += 1
            _event_id = self.input_event_count

        #  handle self-loop in the utg
        if old_state_str == new_state_str and remove_self_loop_transition:
            # delete the transitions including the event from utg
            for new_state_str in self.G[old_state_str]:
                if _event_str in self.G[old_state_str][new_state_str]["events"]:
                    self.G[old_state_str][new_state_str]["events"].pop(_event_str)
            return

        if (old_state_str, new_state_str) not in self.G.edges():
            self.G.add_edge(old_state_str, new_state_str, events={})

        # Fix issue # 22
        self.G[old_state_str][new_state_str]["events"][(_event_str, _event_id)] = {
            "event": _event,
            "id": _event_id,
            "color": event_color,
            "is_inserted_event": is_inserted_event,
            "event_log_file_path": event_log_file_path,
            "event_views_file_path": event_views_file_path if event_views_file_path is not None else []
        }

        self.last_state = new_state
        self.last_state_str = new_state_str

        # Output the utg of gui test
        if output_utg:
            self.output_utg_for_gui_test(utg_output_dir,
                                         insert_start_position=insert_start_position,
                                         independent_trace_len=independent_trace_len,
                                         utg_event_ids_of_test=utg_event_ids_of_test)

    def add_utg_node_for_gui_test(self, state: DeviceState, gui_test_tag=""):

        if state is None:
            return

        state_str = state.state_str + gui_test_tag

        # Note "state_str" already contains the test tag
        if state_str not in self.G.nodes():
            self.G.add_node(state_str, state=state, tag=gui_test_tag)  # set tag of the state

            if self.first_state_str is None:
                self.first_state_str = state_str

        if state.foreground_activity.startswith(self.app.package_name):
            self.reached_activities.add(state.foreground_activity)

    def output_utg_for_gui_test(self, test_output_dir,
                                utg_js_file_name="utg.js",
                                utg_json_file_name="utg.json",
                                insert_start_position=None,
                                independent_trace_len=None,
                                utg_event_ids_of_test=None,
                                screenshot_path_annotation_info: Dict[str, str] = None,
                                transition_annotation_info: Dict[str, List[int]] = None):
        """
        Output current UTG to a js file
        """
        if not test_output_dir:
            return
        utg_file_path = os.path.join(test_output_dir, utg_js_file_name)
        utg_file = open(utg_file_path, "w")
        utg_json_file_path = os.path.join(test_output_dir, utg_json_file_name)
        utg_json_file = open(utg_json_file_path, "w")
        utg_nodes = []
        utg_edges = []
        for state_str in self.G.nodes():
            state = self.G.nodes[state_str]["state"]
            state_tag = self.G.nodes[state_str]["tag"]  # get the state tag
            package_name = state.foreground_activity.split("/")[0]
            activity_name = state.foreground_activity.split("/")[1]
            short_activity_name = activity_name.split(".")[-1] + state_tag
            state_json_file_path = os.path.relpath(state.json_state_path, test_output_dir)

            state_desc = list_to_html_table([
                ("package", package_name),
                ("activity", activity_name),
                ("state_str", state.state_str),
                ("structure_str", state.structure_str)
            ])

            if screenshot_path_annotation_info is not None:
                # check which screenshot path to use if screenshot_path_annotation_info is given
                if state_str not in screenshot_path_annotation_info:
                    # use the the original screenshot path if this screenshot has not been annotated
                    image_path = os.path.relpath(state.screenshot_path, test_output_dir)
                else:
                    # use the new screenshot path if this screenshot has been annotated
                    image_path = os.path.relpath(screenshot_path_annotation_info[state_str], test_output_dir)
            else:
                # directly use the original screenshot path if screenshot_path_annotation_info is not given
                image_path = os.path.relpath(state.screenshot_path, test_output_dir)

            utg_node = {
                "id": state_str,
                "shape": "image",
                "state_json_file_path": state_json_file_path,
                "image": image_path,
                "label": short_activity_name,
                # "group": state.foreground_activity,
                "package": package_name,
                "activity": activity_name,
                "state_str": state_str,
                "structure_str": state.structure_str,
                "title": state_desc,
                "content": "\n".join([package_name, activity_name, state.state_str, state.search_content])
            }

            if state.state_str == self.first_state_str:
                utg_node["label"] += "\n<FIRST>"
                utg_node["font"] = "14px Arial red"
            if state.state_str == self.last_state_str:
                utg_node["label"] += "\n<LAST>"
                utg_node["font"] = "14px Arial red"

            utg_nodes.append(utg_node)

            # TODO uncomment this, this is only for debugging
            utg_nodes = sorted(iter(utg_nodes), key=lambda x: x["id"])

        for state_transition in self.G.edges():
            from_state: str = state_transition[0]
            to_state: str = state_transition[1]

            events = self.G[from_state][to_state]["events"]
            event_short_descs = []
            event_list = []

            for event_str, event_info in sorted(iter(events.items()), key=lambda x: x[1]["id"]):
                event_short_descs.append((event_info["id"], event_str))
                if self.device.adapters[self.device.minicap]:
                    # view_images = ["views/view_" + view["view_str"] + ".jpg"
                    #                for view in event_info["event"].get_views()]
                    view_images = [os.path.relpath(view_file_path, test_output_dir)
                                   for view_file_path in event_info["event_views_file_path"]]
                else:
                    # view_images = ["views/view_" + view["view_str"] + ".png"
                    #                for view in event_info["event"].get_views()]

                    view_images = [os.path.relpath(view_file_path, test_output_dir)
                                   for view_file_path in event_info["event_views_file_path"]]

                    event_list.append({
                        # For the utg of gui test, event_str is a tuple, (event_str, event_id)
                        "event_str": event_str[0],
                        "event_id": event_info["id"],
                        "event_type": event_info["event"].event_type,
                        "is_inserted_event": event_info["is_inserted_event"],
                        "event_log_file_path": os.path.relpath(event_info["event_log_file_path"], test_output_dir),
                        "view_images": view_images,
                        "event_color": event_info['color']
                    })

            utg_edge = {
                "from": from_state,
                "to": to_state,
                "id": from_state + "-->" + to_state,
                "title": list_to_html_table(event_short_descs),
                "label": ", ".join([str(x["event_id"]) for x in event_list]),
                "events": event_list
            }

            # Highlight some utg transitions in color
            for event_dict in event_list:
                event_color = event_dict['event_color']
                event_id = event_dict['event_id']
                if event_color is None:
                    pass
                else:
                    # annotate those inserted events in the mutant test
                    utg_edge["color"] = event_color

                # annotate the transitions of semantic differences
                if transition_annotation_info is not None:
                    test_tag_of_state = self.G.nodes[from_state]['tag']
                    if test_tag_of_state in transition_annotation_info:
                        target_transition_ids = transition_annotation_info[test_tag_of_state]
                        # only apply on the transitions of specified test tag
                        if event_id in target_transition_ids:
                            utg_edge["color"] = COLOR_RED

            utg_edges.append(utg_edge)

            # TODO uncomment this, this is only for debugging
            utg_edges = sorted(iter(utg_edges), key=lambda x: x["label"])

        utg = {
            "nodes": utg_nodes,
            "edges": utg_edges,

            "num_nodes": len(utg_nodes),
            "num_edges": len(utg_edges),
            "num_effective_events": len(self.effective_event_strs),
            "num_reached_activities": len(self.reached_activities),
            "test_date": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "time_spent": (datetime.datetime.now() - self.start_time).total_seconds(),
            "num_input_events": self.input_event_count,

            "device_serial": self.device.serial,

            # "device_model_number": self.device.get_model_number(),
            # "device_sdk_version": self.device.get_sdk_version(),

            "app_sha256": self.app.hashes[2],
            "app_package": self.app.package_name,
            "app_main_activity": self.app.main_activity,
            "app_num_total_activities": len(self.app.activities),

            # test mutation info
            "insert_start_position": insert_start_position if insert_start_position is not None else -1,
            "independent_trace_len": independent_trace_len if independent_trace_len is not None else -1,
            "utg_event_ids_of_test": utg_event_ids_of_test if utg_event_ids_of_test is not None else []
        }

        # dump to "utg.js"
        utg_json = json.dumps(utg, indent=2)
        utg_file.write("var utg = \n")
        utg_file.write(utg_json)
        utg_file.close()
        # dump to "utg.json"
        utg_json_file.write(utg_json)
        utg_json_file.close()

    ###################################

    #  this class is only used to output utg
    def output_utg_for_debug(self, output_dir=None, js_file="utg_recovery.js", json_file="utg_recovery.json",
                             transition_annotation_info=None):
        """
        Output current UTG to a js file
        """
        if not output_dir:
            return
        utg_file_path = os.path.join(output_dir, js_file)
        utg_file = open(utg_file_path, "w")
        utg_json_file_path = os.path.join(output_dir, json_file)
        utg_json_file = open(utg_json_file_path, "w")
        utg_nodes = []
        utg_edges = []
        for state_str in self.G.nodes():
            state = self.G.nodes[state_str]["state"]
            package_name = state.foreground_activity.split("/")[0]
            activity_name = state.foreground_activity.split("/")[1]
            short_activity_name = activity_name.split(".")[-1]

            state_desc = list_to_html_table([
                ("package", package_name),
                ("activity", activity_name),
                ("state_str", state.state_str),
                ("structure_str", state.structure_str)
            ])

            utg_node = {
                "id": state_str,
                "shape": "image",
                "image": os.path.relpath(state.screenshot_path, output_dir),
                "label": short_activity_name,
                # "group": state.foreground_activity,
                "package": package_name,
                "activity": activity_name,
                "state_str": state_str,
                "structure_str": state.structure_str,
                "title": state_desc,
                "content": "\n".join([package_name, activity_name, state.state_str, state.search_content])
            }

            if state.state_str == self.first_state_str:
                utg_node["label"] += "\n<FIRST>"
                utg_node["font"] = "14px Arial red"
            if state.state_str == self.last_state_str:
                utg_node["label"] += "\n<LAST>"
                utg_node["font"] = "14px Arial red"

            utg_nodes.append(utg_node)

            # TODO uncomment this, this is only for debugging
            utg_nodes = sorted(iter(utg_nodes), key=lambda x: x["id"])

        for state_transition in self.G.edges():
            from_state = state_transition[0]
            to_state = state_transition[1]

            events = self.G[from_state][to_state]["events"]
            event_short_descs = []
            event_list = []

            for event_str, event_info in sorted(iter(events.items()), key=lambda x: x[1]["id"]):
                event_short_descs.append((event_info["id"], event_str))
                if self.device.adapters[self.device.minicap]:
                    # view_images = ["views/view_" + view["view_str"] + ".jpg"
                    #                for view in event_info["event"].get_views()]
                    view_images = [os.path.relpath(view_file_path, output_dir)
                                   for view_file_path in event_info["event_views_file_path"]]
                else:
                    # view_images = ["views/view_" + view["view_str"] + ".png"
                    #                for view in event_info["event"].get_views()]
                    view_images = [os.path.relpath(view_file_path, output_dir)
                                   for view_file_path in event_info["event_views_file_path"]]
                event_list.append({
                    "event_str": event_str,
                    "event_id": event_info["id"],
                    "event_type": event_info["event"].event_type,
                    "event_log_file_path": os.path.relpath(event_info["event_log_file_path"], output_dir),
                    "view_images": view_images
                })

            utg_edge = {
                "from": from_state,
                "to": to_state,
                "id": from_state + "-->" + to_state,
                "title": list_to_html_table(event_short_descs),
                "label": ", ".join([str(x["event_id"]) for x in event_list]),
                "events": event_list
            }

            if transition_annotation_info is not None:
                tmp_dict = {}  # {event_id: event_id_annotation}
                for color in transition_annotation_info:
                    if color == "red":
                        target_transition_ids = transition_annotation_info[color]
                        for event_dict in event_list:
                            for target_transition_id in target_transition_ids:
                                if target_transition_id.startswith(str(event_dict['event_id']) + "@"):
                                    if event_dict['event_id'] not in tmp_dict:
                                        tmp_dict[event_dict['event_id']] = target_transition_id
                                    else:
                                        tmp_dict[event_dict['event_id']] = tmp_dict[event_dict['event_id']] \
                                                                           + "," + target_transition_id
                                    if len(tmp_dict) != 0:
                                        utg_edge["color"] = color
                                        utg_edge["label"] = ", ".join(
                                            [str(x["event_id"]) if x["event_id"] not in tmp_dict
                                             else "[" + tmp_dict[x["event_id"]] + "]"
                                             for x in event_list])
                    elif color == "blue":
                        target_transition_ids = transition_annotation_info[color]
                        target_event_ids = [event_dict['event_id'] for event_dict in event_list
                                            if str(event_dict['event_id']) in target_transition_ids]
                        if len(target_event_ids) != 0:
                            utg_edge["color"] = color
                            utg_edge["label"] = ", ".join([str(x["event_id"])
                                                           if x["event_id"] not in target_event_ids
                                                           else "[" + str(x["event_id"]) + "]"
                                                           for x in event_list])

            # # Highlight last transition
            # if state_transition == self.last_transition:
            #     utg_edge["color"] = "red"

            utg_edges.append(utg_edge)

            # TODO uncomment this, this is only for debugging
            utg_edges = sorted(iter(utg_edges), key=lambda x: x["label"])

        utg = {
            "nodes": utg_nodes,
            "edges": utg_edges,

            "num_nodes": len(utg_nodes),
            "num_edges": len(utg_edges),
            "num_effective_events": len(self.effective_event_strs),
            "num_reached_activities": len(self.reached_activities),
            "test_date": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "time_spent": (datetime.datetime.now() - self.start_time).total_seconds(),
            "num_input_events": self.input_event_count,

            "device_serial": self.device.serial,

            # "device_model_number": self.device.get_model_number(),
            # "device_sdk_version": self.device.get_sdk_version(),

            "app_sha256": self.app.hashes[2],
            "app_package": self.app.package_name,
            "app_main_activity": self.app.main_activity,
            "app_num_total_activities": len(self.app.activities),
        }

        utg_json = json.dumps(utg, indent=2)
        utg_file.write("var utg = \n")
        utg_file.write(utg_json)
        utg_file.close()
        # TODO we could optimize: do not generate utg_json_file each time; generate at last time
        utg_json_file.write(utg_json)
        utg_json_file.close()

    def __output_utg(self):
        """
        Output current UTG to a js file
        """
        if not self.device.output_dir:
            return
        utg_file_path = os.path.join(self.device.output_dir, "utg.js")
        utg_file = open(utg_file_path, "w")
        utg_json_file_path = os.path.join(self.device.output_dir, "utg.json")
        utg_json_file = open(utg_json_file_path, "w")
        utg_nodes = []
        utg_edges = []
        for state_str in self.G.nodes():
            state = self.G.nodes[state_str]["state"]
            package_name = state.foreground_activity.split("/")[0]
            activity_name = state.foreground_activity.split("/")[1]
            short_activity_name = activity_name.split(".")[-1]

            state_desc = list_to_html_table([
                ("package", package_name),
                ("activity", activity_name),
                ("state_str", state.state_str),
                ("structure_str", state.structure_str)
            ])

            utg_node = {
                "id": state_str,
                "shape": "image",
                "image": os.path.relpath(state.screenshot_path, self.device.output_dir),
                "state": os.path.relpath(state.json_state_path, self.device.output_dir),
                "label": short_activity_name,
                # "group": state.foreground_activity,
                "package": package_name,
                "activity": activity_name,
                "state_str": state_str,
                "structure_str": state.structure_str,
                "title": state_desc,
                "content": "\n".join([package_name, activity_name, state.state_str, state.search_content])
            }

            if state.state_str == self.first_state_str:
                utg_node["label"] += "\n<FIRST>"
                utg_node["font"] = "14px Arial red"
            if state.state_str == self.last_state_str:
                utg_node["label"] += "\n<LAST>"
                utg_node["font"] = "14px Arial red"

            utg_nodes.append(utg_node)

            # TODO uncomment this, this is only for debugging
            utg_nodes = sorted(iter(utg_nodes), key=lambda x: x["id"])

        for state_transition in self.G.edges():
            from_state = state_transition[0]
            to_state = state_transition[1]

            events = self.G[from_state][to_state]["events"]
            event_short_descs = []
            event_list = []

            for event_str, event_info in sorted(iter(events.items()), key=lambda x: x[1]["id"]):
                event_short_descs.append((event_info["id"], event_str))
                if self.device.adapters[self.device.minicap]:
                    # view_images = ["views/view_" + view["view_str"] + ".jpg"
                    #                for view in event_info["event"].get_views()]
                    view_images = [os.path.relpath(view_file_path, self.device.output_dir)
                                   for view_file_path in
                                   event_info["event_views_file_path"]]  # TODO relpath (main_output_dir)
                else:
                    # view_images = ["views/view_" + view["view_str"] + ".png"
                    #                for view in event_info["event"].get_views()]
                    view_images = [os.path.relpath(view_file_path, self.device.output_dir)
                                   for view_file_path in event_info["event_views_file_path"]]
                event_list.append({
                    "event_str": event_str,
                    "event_id": event_info["id"],
                    "event_type": event_info["event"].event_type,
                    "event_log_file_path": os.path.relpath(event_info["event_log_file_path"], self.device.output_dir)
                    if "event_log_file_path" in event_info else "None",
                    "view_images": view_images
                })

            utg_edge = {
                "from": from_state,
                "to": to_state,
                "id": from_state + "-->" + to_state,
                "title": list_to_html_table(event_short_descs),
                "label": ", ".join([str(x["event_id"]) for x in event_list]),
                "events": event_list
            }

            # # Highlight last transition
            # if state_transition == self.last_transition:
            #     utg_edge["color"] = "red"

            utg_edges.append(utg_edge)

            # TODO uncomment this, this is only for debugging
            utg_edges = sorted(iter(utg_edges), key=lambda x: x["label"])

        utg = {
            "nodes": utg_nodes,
            "edges": utg_edges,

            "num_nodes": len(utg_nodes),
            "num_edges": len(utg_edges),
            "num_effective_events": len(self.effective_event_strs),
            "num_reached_activities": len(self.reached_activities),
            "test_date": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "time_spent": (datetime.datetime.now() - self.start_time).total_seconds(),
            "num_input_events": self.input_event_count,

            "device_serial": self.device.serial,
            "device_model_number": self.device.get_model_number(),
            "device_sdk_version": self.device.get_sdk_version(),

            "app_sha256": self.app.hashes[2],
            "app_package": self.app.package_name,
            "app_main_activity": self.app.main_activity,
            "app_num_total_activities": len(self.app.activities),
        }

        utg_json = json.dumps(utg, indent=2)
        utg_file.write("var utg = \n")
        utg_file.write(utg_json)
        utg_file.close()
        # TODO we could optimize: do not generate utg_json_file each time; generate at last time
        utg_json_file.write(utg_json)
        utg_json_file.close()

    def is_event_explored(self, event, state):
        event_str = event.get_event_str(state)
        return event_str in self.effective_event_strs or event_str in self.ineffective_event_strs

    def is_state_explored(self, state):
        if state.state_str in self.explored_state_strs:
            return True
        for possible_event in state.get_possible_input():
            if not self.is_event_explored(possible_event, state):
                return False
        self.explored_state_strs.add(state.state_str)
        return True

    def is_state_reached(self, state):
        if state.state_str in self.reached_state_strs:
            return True
        self.reached_state_strs.add(state.state_str)
        return False

    def get_reachable_states(self, current_state):
        reachable_states = []
        for target_state_str in nx.descendants(self.G, current_state.state_str):
            target_state = self.G.nodes[target_state_str]["state"]
            reachable_states.append(target_state)
        return reachable_states

    #
    def get_reachable_states_from_first_state(self):
        """
        get the reachable states from the first state of utg
        :return: list. the list of reachable states
        """
        reachable_states = []
        for target_state_str in nx.descendants(self.G, self.first_state_str):
            target_state = self.G.nodes[target_state_str]["state"]
            reachable_states.append(target_state)
        return reachable_states

    def get_event_path(self, current_state, target_state):
        path_events = []
        try:
            states = nx.shortest_path(G=self.G, source=current_state.state_str, target=target_state.state_str)
            if not isinstance(states, list) or len(states) < 2:
                self.logger.warning("Error getting path from %s to %s" %
                                    (current_state.state_str, target_state.state_str))
            start_state = states[0]
            for state in states[1:]:
                edge = self.G[start_state][state]
                edge_event_strs = list(edge["events"].keys())
                if self.random_input:
                    random.shuffle(edge_event_strs)
                path_events.append(edge["events"][edge_event_strs[0]]["event"])
                start_state = state
        except Exception as e:
            print(e)
            self.logger.warning("Cannot find a path from %s to %s" % (current_state.state_str, target_state.state_str))
        return path_events
