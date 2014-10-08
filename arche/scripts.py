from __future__ import unicode_literals
import argparse
#import sys
#import textwrap

from pyramid.paster import bootstrap
import transaction

from arche.utils import find_all_db_objects
from arche.catalog import populate_catalog
from arche.interfaces import ICataloger


def arche_console_script():
    #Move this to some configurable place...
    available_commands = {'reindex_catalog': reindex_catalog,
                          'populate_catalog': populate_catalog_script}
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
    finally:
        env['closer']()
        #Lockfile?

def reindex_catalog(args, root, registry, **kw):
    root.catalog.clear()
    root.document_map.docid_to_address.clear()
    root.document_map.address_to_docid.clear()
    root.document_map.docid_to_metadata.clear()
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
        if i>limit:
            i = 0
            transaction.savepoint()
            print total
    print "-- Process complete. Reindexed %s objects" % total

def populate_catalog_script(args, root, **kw):
    added, changed = populate_catalog(root.catalog)
    print "-- Results: %s added and %s changed" % (len(added), len(changed))
    if added:
        "-- Added indexes: '%s'" % "', '".join(added)
    if changed:
        "-- Changed indexes: '%s'" % "', '".join(changed)
    if added or changed:
        print "-- NOTE: You need to run reindex_catalog too since indexes have changed."
