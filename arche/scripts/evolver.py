from __future__ import unicode_literals

import argparse

from arche.interfaces import IEvolver
from arche.scripting import default_parser


def evolve_packages(env, parsed_ns):
    registry = env['registry']
    root = env['root']
    evolver = registry.queryAdapter(root, IEvolver, name = parsed_ns.package)
    if evolver is None:
        print("No evolver registered for package %r" % parsed_ns.package)
        exit(2)
    if evolver.needs_upgrade:
        print ("Upgrade needed. DB at version %s, "
               "will migrate to %s" % (evolver.db_version, evolver.sw_version))
        evolver.evolve()
    else:
        print ("No upgrade required")


def includeme(config):
    parser = argparse.ArgumentParser(parents=[default_parser])
    parser.add_argument("package", help="Which package to migrate")
    config.add_script(
        evolve_packages,
        name='evolve',
        title="Evolve/Migrate installed packages",
        argparser=parser,
    )
