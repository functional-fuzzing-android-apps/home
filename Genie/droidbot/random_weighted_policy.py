import logging
import random
from typing import List, Dict

from droidbot.input_event import InputEvent, RestartEvent, KeyEvent, IntentEvent, ScrollEvent, TouchEvent, SetTextEvent,\
    LongTouchEvent

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


class WeightedRandomExplorationPolicy(object):
    """
    This policy is adapted from Stoat
    """

    def __init__(self, device, app, random_input, search_method=None,
                 ignore_windows_script=None, restart_threshold=None):

        self.device = device
        self.app = app
        self.random_input = random_input

        self.logger = logging.getLogger(self.__class__.__name__)
        self.search_method = search_method

        self.preferred_buttons = ["yes", "ok", "activate", "detail", "more", "access",
                                  "allow", "check", "agree", "try", "go", "next",
                                  "add", "always", "rename", "delete", "done"]
        self.not_preferred_buttons = ["no", "cancel", "deny"]

        self.__nav_target = None
        self.__nav_num_steps = -1
        self.__num_restarts = 0
        self.__num_steps_outside = 0
        self.__event_trace = ""
        self.__missed_states = set()
        self.__random_explore = False

        self.last_event = None
        self.current_state = None
        self.last_state = None

        self.ignore_windows_script = ignore_windows_script

        # the executable events that appear in the last iteration
        self.last_executable_event_ids: List[str] = []

        # store all input events during the execution history
        #  Data structure:
        #       str: the abstracted (state-free) event signature str
        #       InputEvent: the input event
        self.all_abstracted_input_events: Dict[str, InputEvent] = {}

        # unique executed input events
        self.all_executed_input_events = set()

        # number of unique executed input events
        self.number_of_all_executed_events = 0

        # number of events that have been executed before covering any new input event is executed
        self.number_of_consumed_events = 0

        # # Restart the strategy
        # #   by default, we will not restart the strategy
        # #   if no-zero, do restart after the threshold
        # self.restart_threshold = restart_threshold
        #
        # # number of generated seed tests
        # self.seed_test_cnt = 0
        #
        # # number of events that have been fired by the strategy
        # self.event_count = 0

        self.is_script_activated = False
        self.script_activated_event = None

    def generate_event(self, last_state, last_event, current_state,
                       is_script_activated=False, script_activated_event=None):

        event = None
        self.last_state = last_state
        self.last_event = last_event
        self.current_state = current_state
        self.is_script_activated = is_script_activated
        self.script_activated_event = script_activated_event

        # here we use weighted search policy since there is no available event from the script
        if event is None:

            # Get all possible input events
            possible_input_events = current_state.get_possible_input(
                ignore_windows_script=self.ignore_windows_script)
            event = self.generate_event_based_on_weight(possible_input_events)

        return event

    def store_input_events(self, input_event: InputEvent):
        """
        store the input event
        :param input_event:
        :return:
        """
        input_event_signature = input_event.get_event_signature()
        if input_event_signature in self.all_abstracted_input_events:
            # do nothing if the input event is already recorded
            pass
        else:
            # add the input event if it does not exist
            self.all_abstracted_input_events[input_event_signature] = input_event

        # update the input event's weight

    def update_event_weight(self, input_event_str):

        input_event = self.all_abstracted_input_events[input_event_str]
        input_event.number_of_unexecuted_children_events = 0

        # Re-compute the event weight because this event has been executed at least once

        # Get weight of children (i.e., the number of children that have not been executed before
        #   If the event does not have children, give its default value.
        children_weight = 0
        # Now, we only consider one-level child event
        for child_event_id in input_event.get_children_events():
            # Here we consider the child's weight rather than only its execution time, then we can actually
            #   include the effect of all-level child events
            child_event = self.all_abstracted_input_events[child_event_id]
            # if child_event.get_execution_times() == 0:
            #     # Give a large child weight if the child event has not been executed before.
            #     #   This value will not exceed the effect of initial weight of an un-executed parent event
            #     children_weight += 10
            # else:
            if child_event.executed_times == 0:
                input_event.number_of_unexecuted_children_events += 1
            children_weight += child_event.get_current_event_weight()  # if children_weight < 5 else 0

        # backup the current weight before the update
        input_event.set_last_event_weight(input_event.get_current_event_weight())

        # compute new event weight
        # get execution times of event
        execution_times = input_event.get_execution_times()
        new_event_weight = (input_event.get_last_event_weight() + children_weight) / (
                (execution_times + 1) * (execution_times + 1))
        print(
            "computing weight: event_str(%s), last_event_weight(%f), children_weight(%f), execution_times(%d), new_event weight(%f)" %
            (input_event_str, input_event.get_last_event_weight(), children_weight, (execution_times + 1),
             new_event_weight))

        # update event weight
        input_event.set_current_event_weight(new_event_weight)

    def update_parent_events_weight(self, input_event_str):

        input_event = self.all_abstracted_input_events[input_event_str]
        # update this event's parents
        print("update the event's parents: ")
        for event_str in input_event.get_parent_events():
            self.update_event_weight(event_str)

    def generate_event_based_on_weight(self, possible_input_events):
        """
        generate an event based on current UTG
        @return: InputEvent
        """

        # put all these input events into self.all_abstracted_input_events
        for input_event in possible_input_events:
            self.store_input_events(input_event)

        if self.number_of_all_executed_events == len(self.all_executed_input_events):
            self.number_of_consumed_events += 1
        else:
            self.number_of_consumed_events = 0
            self.number_of_all_executed_events = len(self.all_executed_input_events)
            self.__random_explore = False

        if self.number_of_consumed_events > 100:
            self.__random_explore = True

        self.logger.info("#explored effective input events: %d, #consumed events to cover new views: %d" %
                         (self.number_of_all_executed_events, self.number_of_consumed_events))

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
                    self.__random_explore = False
                else:
                    # Start the app
                    self.__event_trace += EVENT_FLAG_START_APP
                    self.logger.info("Trying to start the app...")

                    # Fix issue #28
                    # update the weight of all input events (including the last input event)
                    if self.last_event is not None:

                        if (isinstance(self.last_event, KeyEvent) and self.last_event.name == 'BACK') \
                                or isinstance(self.last_event, IntentEvent) \
                                or isinstance(self.last_event, RestartEvent):
                            # do not update the children events
                            pass

                        else:
                            # increase the execution time of the last event
                            # Note "BACK" is not maintained in all_abstracted_input_events (If last event is "BACK",
                            #   even if its execution time will be increased, its weight will not be affected.)
                            last_event_str = self.last_event.get_event_signature()
                            print("last event's event_id: %s" % last_event_str)
                            recorded_input_event = self.all_abstracted_input_events[last_event_str]
                            recorded_input_event.incr_execution_times()

                            # update the set of all executed input events
                            self.all_executed_input_events.add(self.last_event.get_event_signature(view_id_free=True))

                            # update the event weight
                            self.update_event_weight(last_event_str)

                            # update the parents' weights of this event
                            self.update_parent_events_weight(last_event_str)

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

        #  ignore specific windows by executing "BACK" event
        elif self.ignore_windows_script is not None and \
                self.ignore_windows_script.is_ignored_window(current_state.foreground_activity):
            # generate a back event
            go_back_event = KeyEvent(name="BACK")
            self.__event_trace += EVENT_FLAG_NAVIGATE
            self.logger.info("Step back to avoid explore %s..." % current_state.foreground_activity)

            return go_back_event

        else:
            # If the app is in foreground
            self.__num_steps_outside = 0

        # START the weighted event selection strategy
        print("I: start weighted event selection strategy ...")

        if self.is_script_activated and self.script_activated_event is not None:
            # update the weight of an event (selected by the weighted strategy) if this event activated the script

            self.update_weights_of_all_events(self.script_activated_event)

            # clear the flag
            self.is_script_activated = False
            self.script_activated_event = None

        else:
            # update the children views of last input event
            if (self.last_event is not None) and len(self.last_executable_event_ids) > 0:
                self.update_children_views_of_an_event(possible_input_events)

            # update the weight of all input events (including the last input event)
            if self.last_event is not None:
                self.update_weights_of_all_events(self.last_event)

        # If no input events on the current page, send "BACK"
        if len(possible_input_events) == 0:
            # Fix issue #
            go_back_event = KeyEvent(name="BACK")
            self.__event_trace += EVENT_FLAG_NAVIGATE
            return go_back_event

        # dump all input events info after update weight
        print("all input events on this UI page: ")
        # for input_event in possible_input_events:
        #     input_event_id = input_event.get_event_signature()
        #     recorded_input_event = self.all_abstracted_input_events[input_event_id]
        #     print("%s, %s" % (input_event_id, recorded_input_event))
        for input_event_id in self.all_abstracted_input_events:
            recorded_input_event = self.all_abstracted_input_events[input_event_id]
            print("%s, W: %s" % (input_event_id, recorded_input_event.get_current_event_weight()))

        if self.__random_explore:

            selected_input_event = self.monkey_based_random_gui_exploration(possible_input_events)
            print("randomly selected input event: ")
            print(selected_input_event.get_event_signature())

        else:

            max_event_weight = -1

            candidate_unexecuted_input_events = []
            candidate_input_events_with_unexecuted_children = []
            candidate_input_events_with_max_weight = []
            preferred_touch_events = []  # record the events with preferred buttons

            # Candidate events analysis
            for input_event in possible_input_events:
                # Note possible_input_events contains new generated events, we still need to
                #   query self.all_abstracted_input_events, which records all the history executed events
                input_event_id = input_event.get_event_signature()
                recorded_input_event = self.all_abstracted_input_events[input_event_id]

                # get the unexecuted events
                if recorded_input_event.get_execution_times() == 0:
                    candidate_unexecuted_input_events.append(input_event)
                elif recorded_input_event.number_of_unexecuted_children_events > 0:
                    candidate_input_events_with_unexecuted_children.append(input_event)
                else:
                    pass

                # check whether this is a preferred touch event
                if isinstance(input_event, TouchEvent) and len(input_event.get_views()) != 0:
                    if "com.android.camera" in self.current_state.foreground_activity:
                        target_view = input_event.get_views()[0]
                        view_content_sensitive_str = \
                            self.current_state.get_view_content_sensitive_str(target_view)
                        if "DONE" in view_content_sensitive_str or "shutter_button" in view_content_sensitive_str:
                            preferred_touch_events.append(input_event)
                    else:
                        view_text = self.get_touch_event_view_text(input_event)
                        if view_text in self.preferred_buttons:
                            preferred_touch_events.append(input_event)

                # get the event weight and collect the candidate events whose weights equal to the max event weight
                event_weight = recorded_input_event.get_current_event_weight()
                if event_weight > max_event_weight:
                    max_event_weight = event_weight
                    candidate_input_events_with_max_weight.clear()
                    # Note append "input_event" rather than "recorded_input_event"
                    candidate_input_events_with_max_weight.append(input_event)
                elif event_weight == max_event_weight:
                    # Note append "input_event" rather than "recorded_input_event"
                    candidate_input_events_with_max_weight.append(input_event)
                else:
                    # do nothing if the event weight is less than max_event_weight
                    pass
            # End

            if len(candidate_unexecuted_input_events) > 0:
                # randomly select an unexecuted event
                print("randomly select an *unexecuted* event.")
                selected_input_event = \
                    candidate_unexecuted_input_events[random.randint(0, len(candidate_unexecuted_input_events) - 1)]

            elif len(candidate_input_events_with_unexecuted_children) > 0:
                # randomly select an event with *unexecuted* children events
                print("randomly select an event with *unexecuted* children events.")
                selected_input_event = candidate_input_events_with_unexecuted_children[
                    random.randint(0, len(candidate_input_events_with_unexecuted_children) - 1)]

            else:

                print("I: the largest weight: %f" % max_event_weight)

                if max_event_weight == 0.0:
                    raise KeyboardInterrupt("The largest weight is zero, quit the weighted exploration!!!")

                print("I: there are total %d events who have the same max weight"
                      % len(candidate_input_events_with_max_weight))
                selected_input_event = \
                    candidate_input_events_with_max_weight[
                        random.randint(0, len(candidate_input_events_with_max_weight) - 1)]

            # check whether to apply the motif event strategy (i.e., prefer commit button than cancel button)
            if isinstance(selected_input_event, TouchEvent) and len(selected_input_event.get_views()) != 0:
                # Specific handling for Android's camera app
                if "com.android.camera" in self.current_state.foreground_activity:
                    target_view = selected_input_event.get_views()[0]
                    view_content_sensitive_str = \
                        self.current_state.get_view_content_sensitive_str(target_view)
                    if ("CANCEL" in view_content_sensitive_str) and len(preferred_touch_events) != 0:
                        random_int = random.randint(0, 100)
                        if random_int > 40:
                            # 30% for not preferred buttons, and 70% for preferred buttons
                            selected_input_event = preferred_touch_events[
                                random.randint(0, len(preferred_touch_events) - 1)]

                else:
                    view_text = self.get_touch_event_view_text(selected_input_event)
                    if view_text in self.not_preferred_buttons:
                        # check whether there exists a preferred button
                        if len(preferred_touch_events) != 0:
                            random_int = random.randint(0, 100)
                            if random_int > 40:
                                # 30% for not preferred buttons, and 70% for preferred buttons
                                selected_input_event = preferred_touch_events[
                                    random.randint(0, len(preferred_touch_events) - 1)]
            # End

            print("I: the selected input event: ")
            print(selected_input_event.get_event_signature())

        # update self.last_executable_event_ids
        self.last_executable_event_ids.clear()
        for input_event in possible_input_events:
            input_event_id = input_event.get_event_signature()
            self.last_executable_event_ids.append(input_event_id)

        if selected_input_event is not None:
            if isinstance(selected_input_event, KeyEvent) and selected_input_event.name == 'BACK':
                print("back")
            self.__event_trace += EVENT_FLAG_EXPLORE
            return selected_input_event

        # If couldn't find a exploration target, stop the app
        stop_app_intent = self.app.get_stop_intent()
        self.logger.info("Cannot find an exploration target. Trying to restart app...")
        self.__event_trace += EVENT_FLAG_STOP_APP
        return IntentEvent(intent=stop_app_intent)

    def update_weights_of_all_events(self, last_event):

        if (isinstance(last_event, KeyEvent) and last_event.name == 'BACK') \
                or isinstance(last_event, IntentEvent) \
                or isinstance(last_event, RestartEvent):
            # do not update the children events
            pass

        else:
            # increase the execution time of the last event
            # Note "BACK" is not maintained in self.all_abstracted_input_events (If last event is "BACK",
            #   even if its execution time will be increased, its weight will not be affected.)
            last_event_str = last_event.get_event_signature()
            print("last event's event_id: %s" % last_event_str)
            if last_event_str in self.all_abstracted_input_events:
                # add an additional check

                recorded_input_event = self.all_abstracted_input_events[last_event_str]
                recorded_input_event.incr_execution_times()

                # update the set of all executed input events
                self.all_executed_input_events.add(last_event.get_event_signature(view_id_free=True))

                # update the event weight
                self.update_event_weight(last_event_str)

                # update the parents' weights of this event
                self.update_parent_events_weight(last_event_str)

    def update_children_views_of_an_event(self, possible_input_events):
        if (isinstance(self.last_event, KeyEvent) and self.last_event.name == 'BACK') \
                or isinstance(self.last_event, ScrollEvent) \
                or isinstance(self.last_event, IntentEvent) \
                or isinstance(self.last_event, RestartEvent):

            # do not update the children events
            pass

        elif not self.current_state.is_new_state(self.last_state):
            # do not update the children events if the current state is not a new state w.r.t the last state
            pass

        else:
            # update the children events
            temp_event_strs = []
            for input_event in possible_input_events:
                temp_event_strs.append(input_event.get_event_signature())

            # Exclude all input events from the current state.
            #   It handles the case :
            #       If the last input have not reached a NEW GUI page (i.e., we stay on the previous GUI page), then
            #       we need to exclude all the events on the current state (because they are not the children
            #       of last input event).
            children_event_strs = set(temp_event_strs).difference(set(self.last_executable_event_ids))

            last_event_str = self.last_event.get_event_signature()
            if last_event_str in self.all_abstracted_input_events:
                # add an additional check
                recorded_input_event = self.all_abstracted_input_events[last_event_str]
                for child_str in children_event_strs:
                    recorded_input_event.add_child_event_id(child_str)
                    self.all_abstracted_input_events[child_str].add_parent_event_id(last_event_str)

    def get_touch_event_view_text(self, touch_event: TouchEvent):
        """
        Precondition: ensure the touch event has a view
        :param touch_event:
        :return:
        """
        target_view = touch_event.get_views()[0]
        view_text = target_view['text'] if target_view['text'] is not None else ''
        view_text = view_text.lower().strip()
        return view_text

    def monkey_based_random_gui_exploration(self, possible_input_events):
        """
        We randomly explore GUI pages like Google Monkey to generate GUI tests
        :param possible_input_events:
        :return: InputEvent
        """

        touch_events = []  # include TouchEvent and SetTextEvent
        long_touch_events = []
        navigation_events = []

        # configurable event type percentages
        pct_touch_event = 45.0
        pct_long_touch_event = 30.0
        pct_navigation_event = 25.0

        for event in possible_input_events:
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
                event = self.random_event(touch_events)
            elif pct_touch_event < rand_pct <= pct_touch_event + pct_long_touch_event:
                self.__event_trace += EVENT_FLAG_EXPLORE
                event = self.random_event(long_touch_events)
            else:
                self.__event_trace += EVENT_FLAG_NAVIGATE
                event = self.random_event(navigation_events)
            if event is not None:
                break
        return event

    def random_event(self, events):
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

