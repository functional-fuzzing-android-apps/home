from argparse import ArgumentParser

from deploy.emulator import emulator_process, ith_emulator_name, wait_ready
from deploy.utils import list_devices

if __name__ == '__main__':
    ap = ArgumentParser()

    ap.add_argument('--avd', dest='avd', required=True)
    ap.add_argument('-o', dest='out', required=True)
    ap.add_argument('--apk', dest='apk', required=True)

    ap.add_argument('--model-construction', '--model', dest='model_construction',
                    default=False, action='store_true')
    ap.add_argument('--model-events-count', dest='model_events_count', type=int, default=2000,
                    help='the number of events allocated for mining the GUI transitional model')

    ap.add_argument('--seed-generation', '--seeds', dest='seed_generation',
                    default=False, action='store_true')
    ap.add_argument('--seeds-count', dest='seeds_count', type=int, default=20,
                    help='the number of random seed tests to be generated')

    ap.add_argument('--mutant-generation', '--mutants', dest='mutant_generation', action='store_true', default=False)
    ap.add_argument('--mutants-per-pos', dest='mutants_per_pos', type=int, default=200,
                    help='the number of mutants to be generated at each insertion position of seed tests')

    ap.add_argument('--seeds-to-mutate', '-s', dest='seeds_to_mutate', type=str, default='all',
                    help='\'all\', or ids of seed tests to run, like \'1;2;3\'')

    ap.add_argument('--offset', default=0, type=int)
    ap.add_argument('--script', default=[], nargs='*')
    ap.add_argument('--config-script', dest='config_script', default=[], nargs='*')
    ap.add_argument('--no-headless', default=False, action='store_true', dest='no_headless')
    ap.add_argument('--dry-run', default=False, action='store_true', dest='dry_run')

    ap.add_argument('--small', default=False, action='store_true')
    ap.add_argument('--big', default=False, action='store_true')
    ap.add_argument('--interval', type=int, default=1)
    ap.add_argument('--no-permission', dest='grant_permission', default=True, action='store_false')

    args = ap.parse_args()

    if args.model_construction or args.seed_generation:
        serial = ith_emulator_name(args.offset)
        if serial in list_devices():
            ap.error('{} already running'.format(serial))

        emulator = emulator_process(args.avd, headless=not args.no_headless, ith=args.offset)
        wait_ready(serial)

    else:
        serial = "emulator-dummy"
        emulator = None

    # the default configuration for model construction and seed/mutant generation
    # model_size, seed_count, mutant_per_pos = (2000, 20, 200)
    model_size, seed_count, mutant_per_pos = (args.model_events_count, args.seeds_count, args.mutants_per_pos)
    if args.small:
        model_size, seed_count, mutant_per_pos = (100, 2, 15)  # (100, 2, 15)
    elif args.big:
        model_size, seed_count, mutant_per_pos = (3200, 100, 300)

    grant_permission = "-grant_perm" if args.grant_permission else ""

    model_cmd = 'python3 -m droidbot.start -d {} -a {}' \
                ' -policy weighted -count {} {}' \
                ' -is_emulator -interval {} -o {}'.format(serial, args.apk, model_size, grant_permission,
                                                          args.interval, args.out)

    base = 'python3 -m droidbot.start -d {} -a {}' \
           ' -policy {{}} -multi-mutant-gen -count 100000' \
           ' -max_seed_test_suite_size {} -max_random_seed_test_length 15' \
           ' -max_independent_trace_length 8 -max_mutants_per_insertion_position {}' \
           ' {} -is_emulator -interval {} -coverage -o {}'.format(serial, args.apk,
                                                                  seed_count,
                                                                  mutant_per_pos,
                                                                  grant_permission,
                                                                  args.interval,
                                                                  args.out)

    seed_and_mutant_generation_cmd = base.format('fuzzing_gen')
    seed_generation_cmd = base.format('fuzzing_gen_seeds')

    mutant_generation_cmd = base.format('fuzzing_gen_mutants') + ' -seeds-to-mutate \'{}\''.format(args.seeds_to_mutate)

    for i in args.config_script:
        model_cmd += ' -config-script {}'.format(i)
        seed_and_mutant_generation_cmd += ' -config-script {}'.format(i)
        seed_generation_cmd += ' -config-script {}'.format(i)
    for i in args.script:
        model_cmd += ' -script {}'.format(i)
        seed_and_mutant_generation_cmd += ' -script {}'.format(i)
        seed_generation_cmd += ' -script {}'.format(i)

    if args.dry_run:
        def run(*args, **kwargs):
            print(args, kwargs)
    else:
        from subprocess import run

    if args.model_construction:
        run(model_cmd, shell=True)
        run('cp {out}/logcat.txt {out}/logcat.model.construction.txt'.format(out=args.out), shell=True)

    if args.seed_generation:
        # generate seed tests
        run(seed_generation_cmd, shell=True)

    if args.mutant_generation:
        # generate seed tests
        run(mutant_generation_cmd, shell=True)

    if emulator is not None:
        emulator.kill()
        emulator.communicate()
