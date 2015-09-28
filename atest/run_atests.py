#!/usr/bin/env python

"""A script for running Robot Framework's acceptance tests.

Usage:  run_atests.py interpreter [options] datasource(s)

Data sources are paths to directories or files under the `atest/robot` folder.

Available options are the same that can be used with Robot Framework.
See its help (e.g. `pybot --help`) for more information.

The specified interpreter is used by acceptance tests under `atest/robot` to
run test cases under `atest/testdata`. It can be simply `python` or `jython`
(if they are in PATH) or a path to a selected interpreter (e.g.
`/usr/bin/python26`) or a path to a robotframework standalone jar (e.g.
`dist/robotframework-2.9dev234.jar`).

As a special case the interpreter value `standalone` will compile a new
standalone jar from the current sources and execute the acceptance tests with
it.

Note that this script itself must always be executed with Python 2.7.

Examples:
$ atest/run_atests.py python --test example atest/robot
$ atest/run_atests.py /opt/jython27/bin/jython atest/robot/tags/tag_doc.robot
"""

import os
import shutil
import signal
import subprocess
import sys
import tempfile
from os.path import abspath, dirname, exists, join, normpath

from interpreter import InterpreterFactory


CURDIR = dirname(abspath(__file__))


sys.path.append(join(CURDIR, '..'))
try:
    from tasks import jar
except ImportError:
    def jar(*args, **kwargs):
        raise RuntimeError("Creating jar distribution requires 'invoke'.")


ARGUMENTS = '''
--doc Robot Framework acceptance tests
--metadata interpreter:{interpreter.name} {interpreter.version} on {interpreter.os}
--variablefile {variable_file};{interpreter.path};{interpreter.name};{interpreter.version}
--pythonpath {pythonpath}
--outputdir {outputdir}
--splitlog
--console dotted
--SuiteStatLevel 3
--TagStatExclude no-*
'''.strip()


def atests(interpreter, *arguments):
    if interpreter == 'standalone':
        interpreter = jar()
    try:
        interpreter = InterpreterFactory(interpreter)
    except ValueError as err:
        sys.exit(err)
    outputdir, tempdir = _get_directories(interpreter)
    arguments = list(_get_arguments(interpreter, outputdir)) + list(arguments)
    return _run(arguments, tempdir)


def _get_directories(interpreter):
    name = interpreter.name.lower().replace(' ', '_')
    outputdir = dos_to_long(join(CURDIR, 'results', name))
    tempdir = dos_to_long(join(tempfile.gettempdir(), 'robottests', name))
    if exists(outputdir):
        shutil.rmtree(outputdir)
    if exists(tempdir):
        shutil.rmtree(tempdir)
    os.makedirs(tempdir)
    return outputdir, tempdir


def _get_arguments(interpreter, outputdir):
    arguments = ARGUMENTS.format(interpreter=interpreter,
                                 variable_file=join(CURDIR, 'interpreter.py'),
                                 pythonpath=join(CURDIR, 'resources'),
                                 outputdir=outputdir)
    for line in arguments.splitlines():
        for part in line.split(' ', 1):
            yield part
    for exclude in interpreter.excludes:
        yield '--exclude'
        yield exclude


def _run(args, tempdir):
    runner = normpath(join(CURDIR, '..', 'src', 'robot', 'run.py'))
    command = [sys.executable, runner] + args
    environ = dict(os.environ, TEMPDIR=tempdir)
    print 'Running command:\n%s\n' % ' '.join(command)
    sys.stdout.flush()
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    return subprocess.call(command, env=environ)


def dos_to_long(path):
    """Convert Windows paths in DOS format (e.g. exampl~1.txt) to long format.

    This is done to avoid problems when later comparing paths. Especially
    IronPython handles DOS paths inconsistently.
    """
    if not (os.name == 'nt' and '~' in path and os.path.exists(path)):
        return path
    from ctypes import create_unicode_buffer, windll
    buf = create_unicode_buffer(500)
    windll.kernel32.GetLongPathNameW(path.decode('mbcs'), buf, 500)
    return buf.value.encode('mbcs')


if __name__ == '__main__':
    if len(sys.argv) == 1 or '--help' in sys.argv:
        print __doc__
        rc = 251
    else:
        rc = atests(*sys.argv[1:])
    sys.exit(rc)