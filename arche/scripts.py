from __future__ import unicode_literals
import argparse

from pyramid.paster import bootstrap
import transaction

from arche.utils import find_all_db_objects
from arche.models.catalog import create_catalog
from arche.interfaces import ICataloger


#NOTE / FIXME:
#This whole section will be refactored - we need to turn scripts into proper
#tasks that can be run either from console or from the web.
#Don't depend on this!


def arche_console_script(*args):
    #Move this to some configurable place...
    available_commands = {'reindex_catalog': reindex_catalog,
                          'create_catalog': create_catalog_script}
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
        print "ERROR: No such command, must be one of:"
        print ", ".join(available_commands.keys())
        return 2
    try:
        print "-- Running %s" % args.command
        available_commands[args.command](args, **env)
        print "-- Committing to database" #FIXME: Optional dry run
        transaction.commit()
    except Exception:
        #FIXME: Do this properly with logging instead
        env['closer']()
        raise
        #Lockfile? zc.lockfile works and is needed by zope

def reindex_catalog(args, root, registry, **kw):
    print "-- Reindexing catalog without clearing it."
    i = 0
    limit = 500
    total = 0
    for obj in find_all_db_objects(root):
        try:
            cataloger = ICataloger(obj)
        except TypeError:
            continue
        cataloger.index_object()
        i += 1
        total += 1
        if i>=limit:
            i = 0
            transaction.savepoint()
            print total
    print "-- Process complete. Reindexed %s objects" % total

def create_catalog_script(args, root, **kw):
    print "-- Clearing/Creating catalog"
    create_catalog(root)
    print "-- Process complete. Run reindex_catalog now."
