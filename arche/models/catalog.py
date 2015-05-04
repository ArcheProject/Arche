from __future__ import unicode_literals
from UserDict import IterableUserDict
from calendar import timegm
from copy import copy
from datetime import datetime

from pyramid.interfaces import IApplicationCreated
from pyramid.threadlocal import get_current_registry
from pyramid.traversal import find_root
from pyramid.traversal import resource_path
from repoze.catalog.catalog import Catalog
from repoze.catalog.document import DocumentMap
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex
from repoze.catalog.indexes.path import CatalogPathIndex
from repoze.catalog.indexes.text import CatalogTextIndex
from six import string_types
from zope.component import adapter
from zope.index.text.lexicon import CaseNormalizer
from zope.index.text.lexicon import Lexicon
from zope.index.text.lexicon import Splitter
from zope.interface import implementer
from zope.interface.verify import verifyClass

from arche import logger
from arche.exceptions import CatalogError
from arche.interfaces import ICatalogIndexes
from arche.interfaces import ICataloger
from arche.interfaces import IIndexedContent
from arche.interfaces import IMetadata
from arche.interfaces import IObjectAddedEvent
from arche.interfaces import IObjectUpdatedEvent
from arche.interfaces import IObjectWillBeRemovedEvent
from arche.interfaces import IRoot
from arche.interfaces import IUser
from arche.interfaces import IWorkflowAfterTransition
from arche.models.workflow import WorkflowException
from arche.models.workflow import get_context_wf
from arche.utils import prep_html_for_search_indexing


@implementer(ICataloger)
@adapter(IIndexedContent)
class Cataloger(object):

    def __init__(self, context):
        self.context = context
        root = find_root(context)
        self.catalog = root.catalog
        self.document_map = root.document_map
        self.path = resource_path(self.context)

    def index_object(self, indexes = None):
        """ Specifying just some indexes will only update
            those indexes. None means all though.
        """
        docid = self.document_map.docid_for_address(self.path)
        if indexes is None:
            indexes = self.catalog.keys()
        if docid is None:
            docid = self.document_map.add(self.path)
            for index in indexes:
                if index in self.catalog:
                    self.catalog[index].index_doc(docid, self.context)
        else:
            for index in indexes:
                if index in self.catalog:
                    self.catalog[index].reindex_doc(docid, self.context)
        self.update_metadata(docid)

    def unindex_object(self):
        docid = self.document_map.docid_for_address(self.path)
        if docid is not None:
            self.catalog.unindex_doc(docid)
            #Metadata will be removed by running remove_docid
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


@implementer(ICatalogIndexes)
class CatalogIndexes(IterableUserDict):
    name = None
    
    def __init__(self, name = None, indexes = None):
        assert isinstance(name, string_types)
        assert isinstance(indexes, dict)
        self.name = name
        self.data = indexes


def add_catalog_indexes(config, package_name, indexes):
    util = CatalogIndexes(package_name, indexes)
    config.registry.registerUtility(util, name = package_name)


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
    attr = ''

    def __init__(self, context):
        self.context = context

    def __call__(self, default = None):
        return getattr(self.context, self.attr, default)


def add_metadata_field(config, metadata_cls):
    verifyClass(IMetadata, metadata_cls)
    #assert IMetadata.implementedBy(metadata_cls), "%r must be a class that implements %r" % (metadata_cls, IMetadata)
    for ar in config.registry.registeredAdapters():
        if ar.provided == IMetadata and ar.name == metadata_cls.name: #pragma : no coverage
            logger.warn("Metadata adapter %r already registered with name %r. Registering %r might override it." % (ar.factory, ar.name, metadata_cls))
    config.registry.registerAdapter(metadata_cls, name = metadata_cls.name)

def create_metadata_field(config, callable_or_attr, name, adapts = IIndexedContent):
    """ Helper method to dynamically create metadata adapters.
        Callables must be methods that can replace the __call__ attribute of the
        Metadata class, or state an attribute to fetch.
    
        Example to add 'uid' to metadata with callable:
        
        def get_uid(self, default = None):
            return getattr(self.context, 'uid', default)
        
        config.create_metadata_field(get_uid, 'uid')
        
        Example with an attribute:
        
        config.create_metadata_field('uid', 'uid')
    """
    @adapter(adapts)
    class _DynMetadata(Metadata):
        pass

    if isinstance(callable_or_attr, string_types):
        _DynMetadata.attr = callable_or_attr
    else:
        _DynMetadata.__call__ = callable_or_attr
    _DynMetadata.name = name
    config.add_metadata_field(_DynMetadata)

def _get_unix_time(dt, default):
    """ The created time is stored in the catalog as unixtime.
        See the time.gmtime and calendar.timegm Python modules for more info.
        http://docs.python.org/library/calendar.html#calendar.timegm
        http://docs.python.org/library/time.html#time.gmtime
    """
    if isinstance(dt, datetime):
        return timegm(dt.timetuple())
    return default

def get_path(context, default): return resource_path(context)

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
        return tuple([x.lower() for x in tags])
    return default

def get_sortable_title(context, default):
    title = getattr(context, 'title', default)
    return title and title.lower() or default

class _AttrDiscriminator(object):
    def __init__(self, attr):
        self.attr = attr

    def __call__(self, context, default):
        return getattr(context, self.attr, default)

def get_searchable_text(context, default):
    root = find_root(context)
    catalog = root.catalog
    registry = get_current_registry()
    discriminators = list(getattr(registry, 'searchable_text_discriminators', ()))
    results = set()
    for index in getattr(registry, 'searchable_text_indexes', ()):
        if index not in catalog: #pragma: no coverage
            #FIXME: Take care of this during startup
            continue
        disc = catalog[index].discriminator
        if isinstance(disc, string_types):
            attr_discriminator = _AttrDiscriminator(disc)
            discriminators.append(attr_discriminator)
        else:
            discriminators.append(catalog[index].discriminator)
    for discriminator in discriminators:
        res = discriminator(context, default)
        if res is default:
            continue
        if not isinstance(res, string_types):
            res = str(res)
        res = res.strip()
        if res:
            results.add(res)
    text = " ".join(results)
    text = text.strip()
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

def create_catalog(root):
    root.catalog = Catalog()
    root.document_map = DocumentMap()
    reg = get_current_registry()
    for util in reg.getAllUtilitiesRegisteredFor(ICatalogIndexes):
        for (key, index) in util.items():
            root.catalog[key] = copy(index)
    _unregister_index_utils(reg)

# Subscribers
def index_object_subscriber(context, event):
    #FIXME: There must be a possibility to link indexes to each other
    reg = get_current_registry()
    changed = getattr(event, 'changed', None)
    if changed is not None:
        changed = set(changed)
        changed.add('searchable_text')
        changed.add('tags') #temp fix until we can link indexes.
    cataloger = reg.queryAdapter(context, ICataloger)
    cataloger.index_object(indexes = changed)

def unindex_object_subscriber(context, event):
    reg = get_current_registry()
    cataloger = reg.queryAdapter(context, ICataloger)
    cataloger.unindex_object()


def add_searchable_text_discriminator(config, discriminator):
    """ A directive to add a discriminator to the index searchable_text.
    
        Discriminators are just a function accepting context and default as argument.
        It should return text, or default.
    """
    assert callable(discriminator), "Not a callable"
    try:
        discriminators = config.registry.searchable_text_discriminators
    except AttributeError:
        discriminators = config.registry.searchable_text_discriminators = set()
    discriminators.add(discriminator)

def add_searchable_text_index(config, name):
    """ Fetch the content of another index and add make it globally searchable.
        (From the index searchable_text)
    """
    assert isinstance(name, string_types), "%r is not a string" % name
    try:
        indexes = config.registry.searchable_text_indexes
    except AttributeError:
        indexes = config.registry.searchable_text_indexes = set()
    indexes.add(name)

_default_searchable_text_indexes = (
    'title',
    'description',
    'userid',
    'first_name',
    'last_name',
)

def _searchable_html_body(context, default):
    body = getattr(context, 'body', default)
    if body != default and isinstance(body, string_types):
        return prep_html_for_search_indexing(body)
    return default

def check_catalog_on_startup(event = None, env = None):
    """ Check that the catalog has all required indexes and that they're up to date.
        Ment to be run by the IApplicationCreated event.
    """
    #Split this into other functions?
    #This should be changed into something more sensible.
    #Env vars?
    from sys import argv
    script_names = ['bin/arche', 'bin/evolver', 'bin/pshell']
    if argv[0] in script_names:
        return
    if env is None:
        from pyramid.scripting import prepare
        env = prepare()
    root = env['root']
    if not IRoot.providedBy(root):
        logger.info("Root object is %r, so check_catalog_on_startup won't run" % root)
        return
    catalog = root.catalog
    reg = env['registry']
    registered_keys = {}
    for util in reg.getAllUtilitiesRegisteredFor(ICatalogIndexes):
        for (key, index) in util.items():
            if key in registered_keys:
                raise CatalogError("Both %r and %r tried to add the same key %r" % (util.name, registered_keys[key], key))
            registered_keys[key] = util.name
            if key not in catalog:
                raise CatalogError("%r requires %r to exist in the catalog." % (util.name, key))
            if catalog[key].discriminator != index.discriminator:
                raise CatalogError("Index stored at %r has a missmatching discriminator. \n"
                                   "Current: %r \n"
                                   "Required: %r \n"
                                   "Required by: %r" % (key, catalog[key].discriminator, index.discriminator, util.name))
    for key in catalog:
        if key not in registered_keys:
            raise CatalogError("Index %r is no longer required and should be removed from the catalog." % key)
    _unregister_index_utils(reg)
    env['closer']()

def _unregister_index_utils(registry):
    for util in registry.getAllUtilitiesRegisteredFor(ICatalogIndexes):
        registry.unregisterUtility(util)

def includeme(config):
    """ Initialise catalog systems.
    """
    config.registry.registerAdapter(Cataloger)

    config.add_subscriber(index_object_subscriber, [IIndexedContent, IObjectAddedEvent])
    config.add_subscriber(index_object_subscriber, [IIndexedContent, IObjectUpdatedEvent])
    config.add_subscriber(index_object_subscriber, [IIndexedContent, IWorkflowAfterTransition])
    config.add_subscriber(unindex_object_subscriber, [IIndexedContent, IObjectWillBeRemovedEvent])
    config.add_subscriber(check_catalog_on_startup, IApplicationCreated)

    config.add_directive('add_catalog_indexes', add_catalog_indexes)
    config.add_directive('add_searchable_text_index', add_searchable_text_index)
    config.add_directive('add_searchable_text_discriminator', add_searchable_text_discriminator)
    config.add_directive('add_metadata_field', add_metadata_field)
    config.add_directive('create_metadata_field', create_metadata_field)

    for index in _default_searchable_text_indexes:
        config.add_searchable_text_index(index)

    config.add_searchable_text_discriminator(_searchable_html_body)

    default_indexes = {
        'title': CatalogFieldIndex('title'),
        'description': CatalogFieldIndex('description'),
        'type_name': CatalogFieldIndex('type_name'),
        'sortable_title': CatalogFieldIndex(get_sortable_title),
        'path': CatalogPathIndex(get_path),
        'searchable_text': CatalogTextIndex(get_searchable_text, lexicon = Lexicon(Splitter(), CaseNormalizer())),
        'uid': CatalogFieldIndex('uid'),
        'tags': CatalogKeywordIndex(get_tags),
        'search_visible': CatalogFieldIndex('search_visible'),
        'date': CatalogFieldIndex(get_date),
        'modified': CatalogFieldIndex(get_modified),
        'created': CatalogFieldIndex(get_created),
        'wf_state': CatalogFieldIndex(get_wf_state),
        'workflow': CatalogFieldIndex(get_workflow),
        'creator': CatalogKeywordIndex(get_creator),
        'userid': CatalogFieldIndex('userid'),
        'email': CatalogFieldIndex('email'),
        'first_name': CatalogFieldIndex('first_name'),
        'last_name': CatalogFieldIndex('last_name'),
        }

    config.add_catalog_indexes(__name__, default_indexes)
