from calendar import timegm
from datetime import datetime

from pyramid.traversal import find_root
from pyramid.traversal import resource_path
from pyramid.threadlocal import get_current_registry
from zope.interface import implementer
from zope.component import adapter
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex
from repoze.catalog.indexes.path import CatalogPathIndex
from repoze.catalog.indexes.text import CatalogTextIndex
from zope.index.text.lexicon import CaseNormalizer
from zope.index.text.lexicon import Lexicon
from zope.index.text.lexicon import Splitter

from arche.interfaces import ICataloger
from arche.interfaces import IUser
from arche.interfaces import IIndexedContent
from arche.interfaces import IObjectAddedEvent
from arche.interfaces import IObjectUpdatedEvent
from arche.interfaces import IObjectWillBeRemovedEvent


_default_searchable_text_indexes = (
    'title',
    'description',
)

@implementer(ICataloger)
@adapter(IIndexedContent)
class Cataloger(object):
    ###FIXME Find all objects in database and reindex them

    def __init__(self, context):
        self.context = context
        root = find_root(context)
        self.catalog = root.catalog
        self.document_map = root.document_map
        self.path = resource_path(self.context)

    def index_object(self):
        docid = self.document_map.docid_for_address(self.path)
        if docid is None:
            docid = self.document_map.add(self.path)
            self.catalog.index_doc(docid, self.context)
        else:
            self.catalog.reindex_doc(docid, self.context)

    def unindex_object(self):
        docid = self.document_map.docid_for_address(self.path)
        if docid is not None:
            self.catalog.unindex_doc(docid)
            self.document_map.remove_address(self.path)

def _get_unix_time(dt, default):
    """ The created time is stored in the catalog as unixtime.
        See the time.gmtime and calendar.timegm Python modules for more info.
        http://docs.python.org/library/calendar.html#calendar.timegm
        http://docs.python.org/library/time.html#time.gmtime
    """
    if isinstance(dt, datetime):
        return timegm(dt.timetuple())
    return default

def get_title(context, default): return getattr(context, 'title', default)
def get_description(context, default): return getattr(context, 'description', default)
def get_type_name(context, default): return getattr(context, 'type_name', default)
def get_path(context, default): return resource_path(context)
def get_uid(context, default): return getattr(context, 'uid', default)
def get_search_visible(context, default): return getattr(context, 'search_visible', default)

def get_date(context, default):
    res = getattr(context, 'date', default)
    return _get_unix_time(res, default)

def get_created(context, default):
    res = getattr(context, 'created', default)
    return _get_unix_time(res, default)

def get_modified(context, default):
    res = getattr(context, 'modified', default)
    return _get_unix_time(res, default)

def get_tags(context, default):
    tags = getattr(context, 'tags', ())
    if tags:
        return tuple(tags)
    return default

def get_sortable_title(context, default):
    title = getattr(context, 'title', default)
    return title and title.lower() or default

def get_userid(context, default):
    if IUser.providedBy(context):
        return context.userid and context.userid or default
    return default

def get_searchable_text(context, default):
    root = find_root(context)
    catalog = root.catalog
    found_text = []
    for index in get_searchable_text_indexes():
        res = catalog[index].discriminator(context, default)
        if res is default:
            continue
        if not isinstance(res, basestring):
            res = str(res)
        res = res.strip()
        if res:
            found_text.append(res)
    text = u" ".join(found_text)
    return text and text or default

def _default_indexes():
    return  {
        'title': CatalogFieldIndex(get_title),
        'description': CatalogFieldIndex(get_description),
        'type_name': CatalogFieldIndex(get_type_name),
        'sortable_title': CatalogFieldIndex(get_sortable_title),
        'path': CatalogPathIndex(get_path),
        'searchable_text': CatalogTextIndex(get_searchable_text, lexicon = Lexicon(Splitter(), CaseNormalizer())),
        'uid': CatalogFieldIndex(get_uid),
        'tags': CatalogKeywordIndex(get_tags),
        'search_visible': CatalogFieldIndex(get_search_visible),
        'date': CatalogFieldIndex(get_date),
        'modified': CatalogFieldIndex(get_modified),
        'created': CatalogFieldIndex(get_created),
    }.items()

def populate_catalog(catalog, indexes = _default_indexes):
    added = set()
    changed = set()
    for (key, index) in indexes():
        if key not in catalog:
            catalog[key] = index
            added.add(key)
            continue
        if not isinstance(catalog[key], index.__class__):
            del catalog[key]
            catalog[key] = index
            changed.add(key)
    return added, changed

# Subscribers
def index_object_subscriber(context, event):
    reg = get_current_registry()
    cataloger = reg.queryAdapter(context, ICataloger)
    #FIXME: plug point for reindexing just some indexes
    cataloger.index_object()

def unindex_object_subscriber(context, event):
    reg = get_current_registry()
    cataloger = reg.queryAdapter(context, ICataloger)
    cataloger.unindex_object()

def get_searchable_text_indexes(registry = None):
    if registry is None:
        registry = get_current_registry()
    return registry._searchable_text_indexes

def includeme(config):
    config.registry.registerAdapter(Cataloger)
    config.add_subscriber(index_object_subscriber, [IIndexedContent, IObjectAddedEvent])
    config.add_subscriber(index_object_subscriber, [IIndexedContent, IObjectUpdatedEvent])
    config.add_subscriber(unindex_object_subscriber, [IIndexedContent, IObjectWillBeRemovedEvent])
    config.registry._searchable_text_indexes = set(_default_searchable_text_indexes)
