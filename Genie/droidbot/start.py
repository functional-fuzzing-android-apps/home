# helper file of droidbot
# it parses command arguments and send the options to droidbot
import argparse
import resource
import sys
from subprocess import run, DEVNULL

from droidbot.device_state import DeviceState
from . import input_manager
from . import input_policy
from . import env_manager
from .droidbot import DroidBot
from .droidmaster import DroidMaster
from .input_policy import POLICY_FUZZ_RUN, UtgBasedPropertyFuzzingPolicy


def parse_args(parser: argparse.ArgumentParser):
    """
    add command line argument to parser
    generate options including host name, port number
    """
    parser.add_argument("-d", action="store", dest="device_serial", required=False,
                        help="The serial number of target device (use `adb devices` to find)")
    parser.add_argument("-a", action="store", dest="apk_path", required=True,
                        help="The file path to target APK")
    parser.add_argument("-o", action="store", dest="output_dir",
                        help="directory of output")

    parser.add_argument('-i', '--model', dest='model_dir', help='model directory')
    parser.add_argument('--overwrite-output-dir', dest='overwrite_output_dir', action='store_true', default=False,
                        help='If to overwrite output_dir when using --model.'
                             'If no, only non-exist output_dir is accepted.')
    parser.add_argument('-seed', '--seed-of-mutant', dest='seed_of_mutant',
                        help='seed of mutant, default is parent of output_dir')
    parser.add_argument('-mutant', '--mutant_dir', dest='mutant_dir',
                        help='the mutant dir that contains all data related to the mutant')

    # parser.add_argument("-env", action="store", dest="env_policy",
    #                     help="policy to set up environment. Supported policies:\n"
    #                          "none\tno environment will be set. App will run in default environment of device; \n"
    #                          "dummy\tadd some fake contacts, SMS log, call log; \n"
    #                          "static\tset environment based on static analysis result; \n"
    #                          "<file>\tget environment policy from a json file.\n")
    parser.add_argument("-policy", action="store", dest="input_policy", default=input_manager.DEFAULT_POLICY,
                        help='Policy to use for test input generation. '
                             'Default: %s.\nSupported policies:\n' % input_manager.DEFAULT_POLICY +
                             '  \"%s\" -- No event will be sent, user should interact manually with device; \n'
                             '  \"%s\" -- Use "adb shell monkey" to send events; \n'
                             '  \"%s\" -- Explore UI using a naive depth-first strategy;\n'
                             '  \"%s\" -- Explore UI using a greedy depth-first strategy;\n'
                             '  \"%s\" -- Explore UI using a naive breadth-first strategy;\n'
                             '  \"%s\" -- Explore UI using a greedy breadth-first strategy;\n'
                             '  \"%s\" -- Explore UI using a script-based exploration strategy;\n'
                             '  \"%s\" -- Model-based property fuzzing strategy;\n'
                             '  \"%s\" -- Explore UI using a weighted strategy;\n'
                             %
                             (
                                 input_policy.POLICY_NONE,
                                 input_policy.POLICY_MONKEY,
                                 input_policy.POLICY_NAIVE_DFS,
                                 input_policy.POLICY_GREEDY_DFS,
                                 input_policy.POLICY_NAIVE_BFS,
                                 input_policy.POLICY_GREEDY_BFS,
                                 input_policy.POLICY_SCRIPT_EXPLORE,
                                 input_policy.POLICY_PROPERTY_FUZZING,
                                 input_policy.POLICY_WEIGHTED
                             ))
    parser.add_argument('-multi-mutant-gen', dest='multi_n', nargs='?',
                        const=True, default=False, type=int,
                        help='Use multi-processing when generating mutants,'
                             'no argument as auto multi-processing,'
                             'int as argument as number of processes')

    # for distributed DroidBot
    parser.add_argument("-distributed", action="store", dest="distributed", choices=["master", "worker"],
                        help="Start DroidBot in distributed mode.")
    parser.add_argument("-master", action="store", dest="master",
                        help="DroidMaster's RPC address")
    parser.add_argument("-qemu_hda", action="store", dest="qemu_hda",
                        help="The QEMU's hda image")
    parser.add_argument("-qemu_no_graphic", action="store_true", dest="qemu_no_graphic",
                        help="Run QEMU with -nograpihc parameter")

    parser.add_argument("-script", action="store", dest="script_path",
                        help="Use a script to customize input events for certain states.")
    parser.add_argument("-config-script", action="store", dest="config_script_path",
                        help="Use a script to record configurations for semantic error checking.")
    parser.add_argument("-ignore-windows-script", action="store", dest="ignore_windows_script_path",
                        help="Use a script to ignore specific windows (e.g., Activities, Dialogs, Menus, etc.) "
                             "during model construction.")
    parser.add_argument("-seed-generation-strategy", action="store", dest="seed_generation_strategy",
                        help="the seed test generation strategy, i.e., \"random\" or \"model\"")
    parser.add_argument("-seeds-to-mutate", dest='seeds_to_mutate', type=str, default='all',
                        help='\'all\', or ids of seed tests to mutate, like \'1;2;3\'')
    parser.add_argument("-do-oracle-checking", dest='do_oracle_checking', action="store_true", default=False,
                        help='do oracle checking when the mutant test was executed')

    parser.add_argument("-count", action="store", dest="count", default=input_manager.DEFAULT_EVENT_COUNT, type=int,
                        help="Number of events to generate in total. Default: %d" % input_manager.DEFAULT_EVENT_COUNT)
    parser.add_argument("-interval", action="store", dest="interval", default=input_manager.DEFAULT_EVENT_INTERVAL,
                        type=int,
                        help="Interval in seconds between each two events. Default: %d" % input_manager.DEFAULT_EVENT_INTERVAL)
    parser.add_argument("-timeout", action="store", dest="timeout", default=input_manager.DEFAULT_TIMEOUT, type=int,
                        help="Timeout in seconds, -1 means unlimited. Default: %d" % input_manager.DEFAULT_TIMEOUT)
    parser.add_argument("-cv", action="store_true", dest="cv_mode",
                        help="Use OpenCV (instead of UIAutomator) to identify UI components. CV mode requires opencv-python installed.")
    #  add option -uiautomator
    parser.add_argument("-uiautomator", action="store_true", dest="uiautomator_mode",
                        help="Use UIAutomator to identify UI components.")

    # options for property-based fuzzing
    parser.add_argument("-max_random_seed_test_length", action="store", dest="max_random_seed_test_length",
                        help="the length of randomly generated seed test for fuzzing")
    parser.add_argument("-max_seed_test_suite_size", action="store", dest="max_seed_test_suite_size",
                        help="the maximum number of seed tests for fuzzing")
    parser.add_argument("-max_independent_trace_length", action="store", dest="max_independent_trace_length",
                        help="the length of independent trace that to be inserted into the seed test")
    parser.add_argument("-max_mutants_per_seed_test", action="store", dest="max_mutants_per_seed_test",
                        help="the maximum number of mutants generated from one seed test")
    parser.add_argument("-max_mutants_per_insertion_position", action="store",
                        dest="max_mutants_per_insertion_position",
                        help="the maximum number of mutants generated from one insertion point")
    parser.add_argument("-utg_abstraction_strategy", action="store", dest="utg_abstraction_strategy",
                        help="the strategy of utg abstraction that is used for mutant generation. We support two"
                             "strategies, i.e., \"content_free\" and \"structure_free\"")
    parser.add_argument("-view_context_str_backtrack_level", action="store", dest="view_context_str_backtrack_level",
                        help="the backtrack level on the view tree for computing context string of any view. "
                             "The best values are 1 or 2. By default we use 1.")
    parser.add_argument("-coverage", action="store_true", dest="dump_coverage_mode",
                        help="dump app coverage.")

    parser.add_argument("-debug", action="store_true", dest="debug_mode",
                        help="Run in debug mode (dump debug messages).")
    parser.add_argument("-random", action="store_true", dest="random_input",
                        help="Add randomness to input events.")
    parser.add_argument("-keep_app", action="store_true", dest="keep_app",
                        help="Keep the app on the device after testing.")
    parser.add_argument("-keep_env", action="store_true", dest="keep_env",
                        help="Keep the test environment (eg. minicap and accessibility service) after testing.")
    parser.add_argument("-use_method_profiling", action="store", dest="profiling_method",
                        help="Record method trace for each event. can be \"full\" or a sampling rate.")
    parser.add_argument("-grant_perm", action="store_true", dest="grant_perm",
                        help="Grant all permissions while installing. Useful for Android 6.0+.")
    parser.add_argument("-is_emulator", action="store_true", dest="is_emulator",
                        help="Declare the target device to be an emulator, which would be treated specially by DroidBot.")
    parser.add_argument("-accessibility_auto", action="store_true", dest="enable_accessibility_hard",
                        help="Enable the accessibility service automatically even though it might require device restart\n(can be useful for Android API level < 23).")
    parser.add_argument("-humanoid", action="store", dest="humanoid",
                        help="Connect to a Humanoid service (addr:port) for more human-like behaviors.")
    parser.add_argument("-ignore_ad", action="store_true", dest="ignore_ad",
                        help="Ignore Ad views by checking resource_id.")
    parser.add_argument("-replay_output", action="store", dest="replay_output",
                        help="The droidbot output directory being replayed.")

    parser.add_argument('-memory-limit', dest='memory', default=0, type=int,
                        help='memory limit in MB')


# noinspection PyShadowingNames
def main(opts):
    """
    the main function
    it starts a droidbot according to the arguments given in cmd line
    """
    import os
    if not os.path.exists(opts.apk_path):
        print("APK does not exist.")
        return
    if not opts.output_dir and opts.cv_mode:
        print("To run in CV mode, you need to specify an output dir (using -o option).")

    # copy model_dir as output_dir
    if opts.model_dir is not None:
        if not os.path.exists(opts.model_dir):
            ap.error('model_dir not exists')
        if os.path.exists(opts.output_dir):
            if not opts.overwrite_output_dir:
                ap.error('need --overwrite-output-dir with -i when output_dir exist')
            elif os.path.samefile(opts.output_dir, opts.model_dir):
                ap.error('output_dir and model_dir should not be same')
            elif opts.overwrite_output_dir and run('rm -rf {}'.format(opts.output_dir), shell=True,
                                                   stdout=DEVNULL, stderr=DEVNULL).returncode != 0:
                ap.error('failed deleting old output_dir')
        if run('cp -r {model} {out}'.format(model=opts.model_dir, out=opts.output_dir),
               shell=True, stdout=DEVNULL, stderr=DEVNULL).returncode != 0:
            ap.error('failed copying model_dir')

    if (opts.seed_of_mutant is not None) == (opts.input_policy == POLICY_FUZZ_RUN):
        if opts.seed_of_mutant and not os.path.exists(opts.seed_of_mutant):
            ap.error('--seed-of-mutant path not exist!')
    else:
        # default to parent of output_dir
        # ap.error('--seed-of-mutant should be used iff with fuzzing_run policy')
        pass

    if opts.seed_generation_strategy is None:
        seed_generation_strategy = UtgBasedPropertyFuzzingPolicy.MONKEY_RANDOM_SEED_GENERATION
    elif opts.seed_generation_strategy not in [UtgBasedPropertyFuzzingPolicy.MONKEY_RANDOM_SEED_GENERATION,
                                               UtgBasedPropertyFuzzingPolicy.MODEL_BASED_RANDOM_SEED_GENERATION]:
        print("seed generation strategy only supports \"monkey\" or \"model\"")
        return
    else:
        seed_generation_strategy = opts.seed_generation_strategy

    if opts.utg_abstraction_strategy is None:
        utg_abstraction_strategy = DeviceState.UTG_ABSTRACTION_BY_CONTENT_FREE

    elif opts.utg_abstraction_strategy not in [DeviceState.UTG_ABSTRACTION_BY_CONTENT_FREE,
                                               DeviceState.UTG_ABSTRACTION_BY_STRUCTURE_FREE]:
        print("seed generation strategy only supports \"monkey\" and \"model\"")
        return
    else:
        utg_abstraction_strategy = opts.utg_abstraction_strategy

    if opts.view_context_str_backtrack_level is None:
        view_context_str_backtrack_level = 1
    elif opts.view_context_str_backtrack_level not in ["1", "2"]:
        print("best values are 1 or 2!")
        return
    else:
        view_context_str_backtrack_level = int(opts.view_context_str_backtrack_level)

    if opts.distributed:
        if opts.distributed == "master":
            start_mode = "master"
        else:
            start_mode = "worker"
    else:
        start_mode = "normal"

    if start_mode == "master":
        droidmaster = DroidMaster(
            app_path=opts.apk_path,
            is_emulator=opts.is_emulator,
            output_dir=opts.output_dir,
            # env_policy=opts.env_policy,
            env_policy=env_manager.POLICY_NONE,
            policy_name=opts.input_policy,
            random_input=opts.random_input,
            script_path=opts.script_path,
            event_interval=opts.interval,
            timeout=opts.timeout,
            event_count=opts.count,
            cv_mode=opts.cv_mode,
            debug_mode=opts.debug_mode,
            keep_app=opts.keep_app,
            keep_env=opts.keep_env,
            profiling_method=opts.profiling_method,
            grant_perm=opts.grant_perm,
            enable_accessibility_hard=opts.enable_accessibility_hard,
            qemu_hda=opts.qemu_hda,
            qemu_no_graphic=opts.qemu_no_graphic,
            humanoid=opts.humanoid,
            ignore_ad=opts.ignore_ad,
            replay_output=opts.replay_output)
        droidmaster.start()
    else:
        #  the entry point
        droidbot = DroidBot(
            app_path=opts.apk_path,
            device_serial=opts.device_serial,
            is_emulator=opts.is_emulator,
            output_dir=opts.output_dir,
            # env_policy=opts.env_policy,
            env_policy=env_manager.POLICY_NONE,
            policy_name=opts.input_policy,
            mutant_gen_n=opts.multi_n,
            random_input=opts.random_input,
            script_path=opts.script_path,
            event_interval=opts.interval,
            timeout=opts.timeout,
            event_count=opts.count,
            cv_mode=opts.cv_mode,
            uiautomator_mode=opts.uiautomator_mode,  #  add uiautomator mode
            debug_mode=opts.debug_mode,
            keep_app=opts.keep_app,
            keep_env=opts.keep_env,
            profiling_method=opts.profiling_method,
            grant_perm=opts.grant_perm,
            enable_accessibility_hard=opts.enable_accessibility_hard,
            master=opts.master,
            humanoid=opts.humanoid,
            ignore_ad=opts.ignore_ad,
            replay_output=opts.replay_output,

            #  the parameters for configuration files
            config_script_path=opts.config_script_path,
            ignore_windows_script_path=opts.ignore_windows_script_path,

            #  the parameters for seeds and mutants
            max_random_seed_test_length=opts.max_random_seed_test_length,
            max_seed_test_suite_size=opts.max_seed_test_suite_size,
            max_independent_trace_length=opts.max_independent_trace_length,
            max_mutants_per_seed_test=opts.max_mutants_per_seed_test if
            opts.max_mutants_per_seed_test is not None else sys.maxsize,
            max_mutants_per_insertion_position=opts.max_mutants_per_insertion_position if
            opts.max_mutants_per_insertion_position is not None else sys.maxsize,

            #  specific running configurations
            seed_of_mutant=opts.seed_of_mutant,
            mutant_dir=opts.mutant_dir,
            seed_generation_strategy=seed_generation_strategy,
            seeds_to_mutate=opts.seeds_to_mutate,
            do_oracle_checking=opts.do_oracle_checking,
            utg_abstraction_strategy=utg_abstraction_strategy,
            view_context_str_backtrack_level=view_context_str_backtrack_level,
            dump_coverage_mode=opts.dump_coverage_mode)

        droidbot.start()
    return


def memory_limit(memory: int):
    _, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (memory * 1024 * 1024, hard))


if __name__ == "__main__":
    print("hello world")
    ap = argparse.ArgumentParser(description="Start DroidBot to test an Android app.",
                                 formatter_class=argparse.RawTextHelpFormatter)
    parse_args(ap)

    opts = ap.parse_args()

    if opts.memory > 0:
        memory_limit(opts.memory)

    try:
        main(opts)
    except MemoryError:
        print('memory limit exceeded', file=sys.stderr)
