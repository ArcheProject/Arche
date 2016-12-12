from __future__ import unicode_literals

import argparse

from arche.scripting import default_parser


def set_passwd_script(env, parsed_ns):
    root = env['root']
    try:
        user = root['users'][parsed_ns.userid]
    except KeyError:
        raise KeyError("No user with id %r found" % parsed_ns.userid)
    user.password = parsed_ns.password
    print("Password for user %r changed" % parsed_ns.userid)


def includeme(config):
    parser = argparse.ArgumentParser(parents=[default_parser])
    parser.add_argument("userid", help="UserID")
    parser.add_argument("password", help="Password")
    config.add_script(
        set_passwd_script,
        name='passwd',
        title="Set password for userid",
        argparser=parser,
    )
