from __future__ import unicode_literals

from arche.models.catalog import create_catalog
from arche.models.catalog import reindex_catalog


def reindex_catalog_script(env, *args):
    print ("-- Reindexing catalog without clearing it.")
    reindex_catalog(env['root'])


def create_catalog_script(env, *args):
    print ( "-- Clearing/Creating catalog")
    create_catalog(env['root'])
    print ( "-- Process complete. Running reindex now.")
    reindex_catalog(env['root'])


def includeme(config):
    config.add_script(
        reindex_catalog_script,
        name='reindex_catalog',
        title="Reindex catalog without clearing it first",
    )
    config.add_script(
        create_catalog_script,
        name='create_catalog',
        title="Create and reindex catalog",
    )
