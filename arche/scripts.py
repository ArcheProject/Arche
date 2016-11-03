from __future__ import unicode_literals
import argparse

from pyramid.paster import bootstrap
import transaction

from arche.models.catalog import create_catalog
from arche.models.catalog import reindex_catalog
from arche.interfaces import IEvolver


#NOTE / FIXME:
#This whole section will be refactored - we need to turn scripts into proper
#tasks that can be run either from console or from the web.
#Don't depend on this!

def arche_console_script(*args):
    #Move this to some configurable place...
    available_commands = {'reindex_catalog': reindex_catalog_script,
                          'create_catalog': create_catalog_script,}
    #description = """Blabla"""
    #usage = """Usage instructions"""
    #Format and make this cuter
    desc = "Available commands: \n"
    for k in available_commands:
        desc += "%s \n \n" % k
    desc += "\n"
    parser = argparse.ArgumentParser(description = desc)
    parser.add_argument("config_uri", help="Paster ini file to load settings from")
    parser.add_argument("command", help="What to actually do")
    args = parser.parse_args()
    
    #print args
    env = bootstrap(args.config_uri)
    
    if args.command not in available_commands:
        print ("ERROR: No such command, must be one of:")
        print (", ".join(available_commands.keys()))
        return 2
    try:
        print ("-- Running %s" % args.command)
        available_commands[args.command](args, **env)
        print ("-- Committing to database") #FIXME: Optional dry run
        transaction.commit()
    except Exception:
        #FIXME: Do this properly with logging instead
        env['closer']()
        raise
        #Lockfile? zc.lockfile works and is needed by zope


def reindex_catalog_script(args, root, registry, **kw):
    print ("-- Reindexing catalog without clearing it.")
    reindex_catalog(root)


def create_catalog_script(args, root, registry, **kw):
    print ( "-- Clearing/Creating catalog")
    create_catalog(root)
    print ( "-- Process complete. Running reindex now.")
    reindex_catalog(root)


def evolve_packages(args, root, registry, **kw):
    evolver = registry.getAdapter(root, IEvolver, name = args.package)
    if evolver.needs_upgrade:
        print ( "Upgrade needed")
        evolver.evolve()
    else:
        print ( "No upgrade required")


def evolve_packages_script(*args):
    parser = argparse.ArgumentParser()
    parser.add_argument("config_uri", help="Paster ini file to load settings from")
    parser.add_argument("package", help="Which package to evolve")
    args = parser.parse_args()
    env = bootstrap(args.config_uri)
    print ( "-- Running evolve scripts in %s") % args.package
    evolve_packages(args, **env)
    print ( "-- Committing to database") #FIXME: Optional dry run
    env['closer']()
