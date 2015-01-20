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
from six import string_types

from arche.interfaces import ICataloger
from arche.interfaces import IIndexedContent
from arche.interfaces import IMetadata
from arche.interfaces import IObjectAddedEvent
from arche.interfaces import IObjectUpdatedEvent
from arche.interfaces import IObjectWillBeRemovedEvent
from arche.interfaces import IWorkflowAfterTransition
from arche.models.workflow import WorkflowException
from arche.models.workflow import get_context_wf
from arche import logger


@implementer(ICataloger)
@adapter(IIndexedContent)
class Cataloger(object):

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
        self.update_metadata(docid)

    def unindex_object(self):
        docid = self.document_map.docid_for_address(self.path)
        if docid is not None:
            self.catalog.unindex_doc(docid)
            #Metadata will be removed by running remove_docid
            #self.document_map.remove_metadata(docid)
            self.document_map.remove_docid(docid)

    def update_metadata(self, docid):
        """ Clean up or add metadata to the document map. """
        metadata = self.get_metadata()
        if metadata:
            self.document_map.add_metadata(docid, metadata)
        else:
            try:
                self.document_map.remove_metadata(docid)
            except KeyError:
                pass #No metadata existed

    def get_metadata(self):
        """ Return metadata for current context, if any. """
        results = {}
        marker = object()
        registry = get_current_registry()
        for (name, metadata) in registry.getAdapters([self.context], IMetadata):
            #Catch exceptions? Probably
            res = metadata(marker)
            if res is not marker:
                results[name] = res
        return results


@implementer(IMetadata)
class Metadata(object):
    """ Use this to create metadata fields stored in the catalog.
        Subclass, pick a name and return something that is usable as metadata
        when called.
        You need to make it adapt something first. Only objects stored in the catalog are valid.
        
        See repoze.catalog on metadata.
        
        Example:
        
        @adapter(IIndexedContent)
        class MyUppercaseTitle(Metadata):
            name = 'uppercase_title'
            
            def __call__(self, default = None):
                return self.context.title.upper()
        
        config.add_metadata_field(MyUppercaseTitle)
    """
    name = ''

    def __init__(self, context):
        self.context = context

    def __call__(self, default = None):
        raise NotImplementedError() #pragma : no coverage


def add_metadata_field(config, metadata_cls):
    assert IMetadata.implementedBy(metadata_cls), "%r must be a class that implements %r" % (metadata_cls, IMetadata)
    for ar in config.registry.registeredAdapters():
        if ar.provided == IMetadata and ar.name == metadata_cls.name: #pragma : no coverage
            logger.warn("Metadata adapter %r already registered with name %r. Registering %r might override it." % (ar.factory, ar.name, metadata_cls))
    config.registry.registerAdapter(metadata_cls, name = metadata_cls.name)

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

def get_searchable_text(context, default):
    root = find_root(context)
    catalog = root.catalog
    found_text = []
    for index in get_searchable_text_indexes():
        if index not in catalog:
            #Log?
            continue
        res = catalog[index].discriminator(context, default)
        if res is default:
            continue
        if not isinstance(res, string_types):
            res = str(res)
        res = res.strip()
        if res:
            found_text.append(res)
    text = u" ".join(found_text)
    return text and text or default

def get_wf_state(context, default):
    try:
        wf = get_context_wf(context)
    except WorkflowException:
        return default
    return wf and wf.state or default

def get_workflow(context, default):
    try:
        wf = get_context_wf(context)
    except WorkflowException:
        return default
    return wf and wf.name or default

def get_creator(context, default):
    creator = getattr(context, 'creator', None)
    return creator and tuple(creator) or default
    

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
        'wf_state': CatalogFieldIndex(get_wf_state),
        'workflow': CatalogFieldIndex(get_workflow),
        'creator': CatalogFieldIndex(get_creator),
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
    return getattr(registry, '_searchable_text_indexes', ())

def add_searchable_text_index(config, name):
    assert isinstance(name, string_types), "%r is not a string" % name
    indexes = config.registry._searchable_text_indexes
    indexes.add(name)

_default_searchable_text_indexes = (
    'title',
    'description',
)


def includeme(config):
    config.registry.registerAdapter(Cataloger)
    config.add_subscriber(index_object_subscriber, [IIndexedContent, IObjectAddedEvent])
    config.add_subscriber(index_object_subscriber, [IIndexedContent, IObjectUpdatedEvent])
    config.add_subscriber(index_object_subscriber, [IIndexedContent, IWorkflowAfterTransition])
    config.add_subscriber(unindex_object_subscriber, [IIndexedContent, IObjectWillBeRemovedEvent])
    config.registry._searchable_text_indexes = set(_default_searchable_text_indexes)
    config.add_directive('add_searchable_text_index', add_searchable_text_index)
    config.add_directive('add_metadata_field', add_metadata_field)
