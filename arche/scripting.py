import argparse
from sys import argv
from sys import exc_info
import traceback

from arche.utils import format_traceback
from transaction import commit
from transaction import abort
from pyramid.paster import bootstrap
from zc.lockfile import LockFile
from zope.interface import implementer

from arche.interfaces import IScript


_runner_parser = argparse.ArgumentParser(add_help=False)
_runner_parser.add_argument("config_uri", help="Paster ini file to load settings from")
_runner_parser.add_argument("-l", "--list",
                           help="List available commands and exit",
                           action="store_true")

_runner_with_cmd = argparse.ArgumentParser(add_help=False, parents=[_runner_parser])
_runner_with_cmd.add_argument("command", help="What to actually do")

default_parser = argparse.ArgumentParser(add_help=False, parents=[_runner_with_cmd])
default_parser.add_argument("-d", "--dry-run",
                    help="Dry-run, don't commit anything",
                    action="store_true")
default_parser.add_argument("-L", "--lock",
                            help=("Lock-file directory. If specified, makes sure "
                                  "only one instance of the script is run. "
                                  "A lockfile will be created in that dir with the scripts name."))
_default_with_help = argparse.ArgumentParser(parents=[default_parser])


@implementer(IScript)
class Script(object):
    name = ""
    title = ""
    description = ""
    callable = None
    can_commit = True
    argparser = None

    def __init__(self, _callable, argparser=_default_with_help, **kw):
        self.callable = _callable
        self.argparser = argparser
        for k, v in kw.items():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                raise Exception("No attribute called %r" % k)

    def __call__(self, env, script_args):
        parsed_ns = self.argparser.parse_args(script_args)
        lock = self.maybe_lock(parsed_ns)
        self.start(env, parsed_ns)
        try:
            self.callable(env, parsed_ns)
            if self.can_commit:
                if parsed_ns.dry_run:
                    print ("-- Dry run - no commit")
                    abort()
                else:
                    print ("-- Committing to database")
                    commit()
            else:
                #Just to be sure
                abort()
        except Exception as exc:
            if self.can_commit:
                print ("-- ERROR: Script caused an exception - aborting commit")
                print (_format_traceback())
            abort()
            print (format_traceback())
        finally:
            self.cleanup(env, parsed_ns)
            if lock:
                lock.close()

    def start(self, env, parsed_ns):
        pass

    def cleanup(self, env, parsed_ns):
        env['closer']()

    def maybe_lock(self, parsed_ns):
        if parsed_ns.lock:
            fn = parsed_ns.lock + self.name + '.lock'
            return LockFile(fn)


def run_arche_script(args=()):
    if not args:
        #To allow testing injection
        args = argv[1:]
    base_ns, script_args = _runner_parser.parse_known_args(args)
    env = bootstrap(base_ns.config_uri)
    reg = env['registry']
    scripts = dict(reg.getUtilitiesFor(IScript))
    if base_ns.list:
        _print_registered(scripts)
        exit(2)
    base_ns, script_args = _runner_with_cmd.parse_known_args(args)
    if base_ns.command not in scripts:
        print("\nNo such script %r" % base_ns.command)
        _print_registered(scripts)
        exit(2)
    scripts[base_ns.command](env, args)


def _format_traceback():
    exception_list = traceback.format_stack()
    exception_list = exception_list[:-2]
    exception_list.extend(traceback.format_tb(exc_info()[2]))
    exception_list.extend(traceback.format_exception_only(exc_info()[0], exc_info()[1]))
    exception_str = "-- Traceback (most recent call last):\n"
    exception_str += "".join(exception_list)
    return exception_str


def _print_registered(scripts):
    default_padding = 10
    for k in scripts:
        if len(k) + 5 > default_padding:
            default_padding = len(k) + 5
    print("-"*80)
    print("Registered script names:\n")
    for name, script in scripts.items():
        print(name.ljust(default_padding) + script.title)
    print ("\nFor more information, use the help-command + name of script")


def add_script(config, callable, name=None, **kw):
    if name is None:
        name = callable.__name__
    script = Script(callable, name=name, **kw)
    config.registry.registerUtility(script, name = name)


def help_script(env, parsed_ns):
    reg = env['registry']
    scripts = dict(reg.getUtilitiesFor(IScript))
    if parsed_ns.help_cmd in scripts:
        script = scripts[parsed_ns.help_cmd]
        print("\n")
        print (script.title)
        print ("="*80)
        if script.argparser:
            script.argparser.print_help()
    else:
        print ("No command called %r" % parsed_ns.help_cmd)


def includeme(config):
    config.add_directive('add_script', add_script)
    parser = argparse.ArgumentParser(parents=[default_parser])
    parser.add_argument("help_cmd", help="Which command to display help for")
    config.add_script(
        help_script,
        name='help',
        title = 'Help - specify command to see more info',
        argparser = parser,
        can_commit = False,
    )
