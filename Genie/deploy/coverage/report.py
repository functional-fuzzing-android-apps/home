from argparse import ArgumentParser
from os.path import join
from subprocess import run

from ..coverage import jacoco_jar

if __name__ == '__main__':
    ap = ArgumentParser()

    ap.add_argument('--project', '-p', required=True)
    ap.add_argument('--source', '-s', default='app/src/main/java/')
    ap.add_argument('--class', '-c', dest='classes', default='app/build/intermediates/classes/')

    ap.add_argument('ec', nargs='+')
    ap.add_argument('report', metavar='HTML-REPORT')

    args = ap.parse_args()

    run(['java', '-jar', jacoco_jar, 'report'] +
        list(args.ec) +
        ['--classfiles', join(args.project, args.classes), '--sourcefiles', join(args.project, args.source)] +
        ['--html', args.report])
