from argparse import ArgumentParser
from pathlib import Path

from . import merge

if __name__ == '__main__':
    ap = ArgumentParser()

    ap.add_argument('output')

    for i in 'seed', 'mutant':
        ap.add_argument('--{}-cov-out'.format(i), dest='{}_output'.format(i),
                        nargs='?', const=True, default=False,
                        help='merge coverage of {0} into specific file,'
                             'default = `<output>/{0}.ec`'.format(i))

        ap.add_argument('--{}s'.format(i), dest='{}s'.format(i),
                        default='all',
                        help='\'all\', or ids of {} to merge, like \'1;2;3\'')

    args = ap.parse_args()

    args.output = Path(args.output)

    if not args.output.exists():
        ap.error('{} not exists'.format(args.output))

    for i in ('seed', 'mutant'):
        args_key = '{}_output'.format(i)
        args_value: str = getattr(args, args_key)
        if args_value is False:
            pass
        elif args_value is True:
            setattr(args, args_key, args.output / '{}.ec'.format(i))
        if args_value is not False and getattr(args, args_key).exists():
            ap.error('{} already exists'.format(getattr(args, args_key)))

        args_key = '{}s'.format(i)
        args_value = getattr(args, args_key)
        if args_value == 'all':
            pass
        else:
            setattr(args, args_key, {i for i in args_value.split(';') if i})

    seed_covs = []
    mutant_covs = []
    for seed in (args.output / 'seed-tests').glob('seed-test-*'):
        if not args.seeds == 'all' and seed.name.split('-')[2] not in args.seeds:
            # skip this seed
            continue
        if args.seed_output:
            seed_cov = seed / 'coverage.ec'
            if seed_cov.exists():
                seed_covs.append(str(seed_cov))
        if args.mutant_output:
            for m in seed.glob('mutant-*'):
                if not args.mutants == 'all' and m.name.split('-')[1] not in args.mutants:
                    # skip this mutant
                    continue
                mutant_cov = m / 'coverage.ec'
                if mutant_cov.exists():
                    mutant_covs.append(str(mutant_cov))

    if seed_covs:
        merge(str(args.seed_output), seed_covs)
    if mutant_covs:
        merge(str(args.mutant_output), mutant_covs)
