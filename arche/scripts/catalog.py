from __future__ import unicode_literals

import argparse

from arche.exceptions import CatalogNeedsUpdate
from arche.models.catalog import check_catalog
from arche.models.catalog import create_catalog
from arche.models.catalog import reindex_catalog
from arche.models.catalog import quick_reindex
from arche.scripting import default_parser


def reindex_catalog_script(env, *args):
    print ("-- Reindexing catalog without clearing it.")
    reindex_catalog(env['root'])


def create_catalog_script(env, *args):
    print ( "-- Clearing/Creating catalog")
    create_catalog(env['root'])
    print ( "-- Process complete. You should run reindex now.")


def quick_reindex_script(env, parsed_ns):
    if parsed_ns.indexes is None:
        print ("-- Reindexing everything that already exists in the catalog.")
    else:
        print ("-- Reindexing specified indexes")
    request = env['request']
    quick_reindex(request, parsed_ns.indexes)


def check_catalog_script(env, *args):
    """ Check if the catalog needs an update from the command line.
    """
    root, registry = env['root'], env['registry']
    index_needs_indexing, indexes_to_remove = check_catalog(root, registry)
    if index_needs_indexing:
        raise CatalogNeedsUpdate("The folllowing indexes needs update: '%s'" % "', '".join(index_needs_indexing))
    if indexes_to_remove:
        raise CatalogNeedsUpdate("The folllowing indexes should be removed: '%s'" % "', '".join(indexes_to_remove))


def includeme(config):
    config.add_script(
        reindex_catalog_script,
        name='reindex_catalog',
        title="Reindex catalog without clearing it first",
        can_commit=True,
    )
    config.add_script(
        create_catalog_script,
        name='create_catalog',
        title="Create and reindex catalog",
        can_commit=True,
    )
    parser = argparse.ArgumentParser(parents=[default_parser])
    parser.add_argument("-i", dest='indexes',
                        action='append',
                        help="Index names to do quick reindex on.")
    config.add_script(
        quick_reindex_script,
        name='quick_reindex',
        title="Quick reindex a specific index",
        argparser=parser,
        can_commit=True,
    )
    config.add_script(
        check_catalog_script,
        name='check_catalog',
        title="Check if the catalog needs an update",
        can_commit=False,
    )
