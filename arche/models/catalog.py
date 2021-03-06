from __future__ import unicode_literals

from calendar import timegm
from copy import copy
from datetime import datetime
from os import getenv

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
from repoze.catalog.query import Any, Eq
from six import string_types
from zope.component import adapter
from zope.index.text.lexicon import CaseNormalizer
from zope.index.text.lexicon import Lexicon
from zope.index.text.lexicon import Splitter
from zope.interface import implementer
from zope.interface.verify import verifyClass

from arche import logger
from arche.compat import IterableUserDict
from arche.exceptions import CatalogConfigError
from arche.interfaces import ICatalogIndexes
from arche.interfaces import ICataloger
from arche.interfaces import IIndexedContent
from arche.interfaces import ILocalRoles
from arche.interfaces import IMetadata
from arche.interfaces import IObjectAddedEvent
from arche.interfaces import IObjectUpdatedEvent
from arche.interfaces import IObjectWillBeRemovedEvent
from arche.interfaces import IRoot
from arche.interfaces import IWorkflowAfterTransition
from arche.models.workflow import WorkflowException
from arche.models.workflow import get_context_wf
from arche.utils import find_all_db_objects
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
                    try:
                        self.catalog[index].index_doc(docid, self.context)
                    except Exception: # pragma: no coverage
                        logger.warn("Failing index: %s", index)
                        raise
        else:
            for index in indexes:
                if index in self.catalog:
                    try:
                        self.catalog[index].reindex_doc(docid, self.context)
                    except Exception: # pragma: no coverage
                        logger.warn("Failing index: %s", index)
                        raise
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
    config.registry.registerUtility(util, name=package_name, provided=ICatalogIndexes)
    config.update_index_info(indexes)


_default_marker = object()


class CatalogIndexHelper(object):
    """ Keeps track of which indexes relate to what content. See the update method."""

    def __init__(self):
        self.data = {}

    def update(self, name, linked=_default_marker, type_names=_default_marker):
        """ Update info for an index

            name
                Name of the index

            linked
                Which changed attributes or other indexes should this update for?
                The name of the index is assumed here too.
                Notable values:
                    default is the name of the index
                    None means everything
                    Or specify a list of attributes. Searchable text should for instance
                    update for anything searchable.

            type_names
                This index is only for specific content types. If specified as a list,
                only reindex this index if the content type is listed here.
                Mostly usable for quick reindex.
        """
        assert isinstance(name, string_types), "'name' must be a string"
        if isinstance(linked, string_types):
            linked = set([linked])
        if isinstance(type_names, string_types):
            type_names = set([type_names])
        if name not in self:
            self[name] = IndexInfo(name, linked, type_names)
        else:
            info = self[name]
            if linked != _default_marker:
                if linked is None:
                    info.linked = None
                else:
                    if info.linked is None:
                        info.linked = set()
                    info.linked.update(linked)
            if type_names != _default_marker:
                if type_names is None:
                    info.type_names = None
                else:
                    if info.type_names is None:
                        info.type_names = set()
                    info.type_names.update(type_names)

    def get_limit_types(self, index_names):
        """ Check if it's possible to reindex the indexes listed in
            index names by only touching a few existing types.

            Returns a set of type_names if it's possible, otherwise None
        """
        if index_names is None:
            # All
            return
        found_types = set()
        for name in index_names:
            try:
                if self[name].type_names is None:
                    return
            except KeyError:
                return
            found_types.update(self[name].type_names)
        return found_types

    def get_required(self, names):
        """ Returns a set of which indexes requires updates,
            given the list of other index names or attributes.

            For instance, searchable_text must always be updated when title updates."""
        # FIXME This function must be able to recurse into other index names without crashing
        if names is None:
            # All indexes
            return
        found = set(names)
        names = set(names)
        for info in self.values():
            if info.linked is None:
                found.add(info.name)
            elif info.linked & names:
                found.add(info.name)
        return found

    def __setitem__(self, key, value):
        assert isinstance(value, IndexInfo)
        self.data[key] = value

    def __getitem__(self, key):
        return self.data[key]

    def __contains__(self, key):
        return key in self.data

    def values(self):
        return self.data.values()


class IndexInfo(object):
    """ Describes a catalog index that exists or should exist in the catalog.
    """
    name = ''
    linked = None
    type_names = None

    def __init__(self, name, linked=_default_marker, type_names=None):
        assert name and isinstance(name, string_types), "'name' param must be a string"
        self.name = name
        if linked == _default_marker:
            linked = set([name])
        if linked:
            linked = set(linked)
            if name not in linked:
                linked.add(name)
        self.linked = linked
        if type_names == _default_marker:
            type_names = None
        self.type_names = type_names


def update_index_info(config, names, linked=_default_marker, type_names=_default_marker):
    if isinstance(names, string_types):
        names = [names]
    for name in names:
        config.registry.catalog_indexhelper.update(name, linked=linked, type_names=type_names)


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
    for ar in config.registry.registeredAdapters():
        if ar.provided == IMetadata and ar.name == metadata_cls.name: #pragma : no coverage
            logger.warn("Metadata adapter %r already registered with name %r. "
                        "Registering %r might override it." % (ar.factory, ar.name, metadata_cls))
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
    registry = get_current_registry()
    for index in registry.catalog_indexhelper['searchable_text'].linked:
        if index not in catalog: #pragma: no coverage
            # In case a bad name was linked in searchable_text, no reason to die because of it.
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


def get_local_roles(context, default):
    """ Return userids of anyone having a local role within context.
        Not the actual roles!
    """
    if ILocalRoles.providedBy(context):
        return tuple(context.local_roles.keys())
    return default


def get_relation(context, default):
    """ Attribute with a list of relations. """
    if hasattr(context, 'relation'):
        return tuple(context.relation)
    return default


def create_catalog(root):
    root.catalog = Catalog()
    root.document_map = DocumentMap()
    reg = get_current_registry()
    for util in reg.getAllUtilitiesRegisteredFor(ICatalogIndexes):
        for (key, index) in util.items():
            root.catalog[key] = copy(index)
    _unregister_index_utils(registry=reg)


# Subscribers
def index_object_subscriber(context, event):
    reg = get_current_registry()
    changed = getattr(event, 'changed', None)
    if changed is not None:
        changed = set(changed)
        changed = reg.catalog_indexhelper.get_required(changed)
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


def add_searchable_text_index(config, names):
    """ Fetch the content of another index or attribute and add make it globally searchable.
        (From the index searchable_text)
    """
    if isinstance(names, string_types):
        names = [names]
    config.update_index_info('searchable_text', names)


def _searchable_html_body(context, default):
    body = getattr(context, 'body', default)
    if body != default and isinstance(body, string_types):
        return prep_html_for_search_indexing(body)
    return default


def _savepoint_callback(current):
    logger.info("Reindexing-progress: %s", current)


def reindex_catalog(root, savepoint_limit = 1000, savepoint_callback=_savepoint_callback):
    i = 0
    total = 0
    import transaction
    logger.info("Reindexing catalog")
    for obj in find_all_db_objects(root):
        try:
            cataloger = ICataloger(obj)
        except TypeError:
            continue
        cataloger.index_object()
        i += 1
        total += 1
        if i>=savepoint_limit:
            i = 0
            transaction.savepoint()
            savepoint_callback(total)
    logger.info("Process complete. %s objects reindexed", total)


def check_catalog(root, registry):
    if not IRoot.providedBy(root):
        logger.info("Root object is %r, so check_catalog_on_startup won't run" % root)
        return [], []
        #return _commit_and_cleanup(env['closer'], commit=False, registry=reg)
    catalog = root.catalog
    registered_keys = {}
    index_needs_indexing = []
    for util in registry.getAllUtilitiesRegisteredFor(ICatalogIndexes):
        for (key, index) in util.items():
            if key in registered_keys:
                raise CatalogConfigError("Both %r and %r tried to add the same key %r"
                                         % (util.name, registered_keys[key], key))
            registered_keys[key] = util.name
            if key not in catalog:
                if key == 'type_name':
                    raise CatalogConfigError(
                        "'type_name' was missing in the catalog."
                        "This shouldn't happen, so you need to to a full reindex with:\n"
                        "arche <paster.ini> create_catalog && arche <paster.ini> reindex_catalog")
                logger.warn("%r requires the index %r, will add it and run index operation", util.name, key)
                index_needs_indexing.append(key)
                catalog[key] = index
                continue
            if catalog[key].discriminator != index.discriminator:
                logger.warn("%r exists, but the discriminator has changed. "
                            "It will need to be readded and reindexed.", key)
                del catalog[key]
                index_needs_indexing.append(key)
                catalog[key] = index
    # Clean up unused indexes
    indexes_to_remove = set()
    for key in catalog:
        if key not in registered_keys:
            indexes_to_remove.add(key)
    return index_needs_indexing, indexes_to_remove


def check_catalog_on_startup(event = None, env = None):
    """ Check that the catalog has all required indexes and that they're up to date.
        Ment to be run by the IApplicationCreated event.
    """
    def _commit_and_cleanup(closer, request, commit=False, registry=None):
        if commit:
            try:
                commit_func = request.tm.commit
            except AttributeError:
                from transaction import commit
                commit_func = commit
            commit_func()
        _unregister_index_utils(registry)
        closer()

    #Split this into other functions?
    #This should be changed into something more sensible.
    #Env vars?
    from sys import argv
    #FIXME: This makes arche unusable on windows, or if someone types
    #"./bin/arche" this won't work.
    script_names = ['bin/arche', 'bin/pshell']
    if argv[0] in script_names or getenv("ARCHE_NO_CATALOG_CHECK"):
        return _unregister_index_utils()
    if env is None:
        from pyramid.scripting import prepare
        env = prepare()

    root = env['root']
    registry = env['registry']
    request = env['request']
    index_needs_indexing, indexes_to_remove = check_catalog(root, registry)

    for key in indexes_to_remove:
        logger.warn("Removing catalog index '%s' since it's not registered anywhere.", key)
        del root.catalog[key]
    # Finally reindex any that needs reindexing
    if index_needs_indexing:
        quick_reindex(request, index_needs_indexing)
    _commit_and_cleanup(env['closer'], request, commit=bool(index_needs_indexing or indexes_to_remove), registry=registry)


def quick_reindex(request, indexes):
    if not bool(len(request.root.document_map.docid_to_address)):
        raise Exception("There's nothing in the catalog, so quick reindex won't work. "
                        "Use reindex_catalog command instead.")
    indexhelper = request.registry.catalog_indexhelper
    limit_types = indexhelper.get_limit_types(indexes)
    if limit_types:
        query = Any('type_name', list(limit_types))
        res, docids = request.root.catalog.query(query)
        total = res.total
    else:
        total = len(request.root.document_map.docid_to_address)
        docids = request.root.document_map.docid_to_address
    required = indexhelper.get_required(indexes)
    if required is None:
        # None means all here
        required = list(request.root.catalog.keys())
    else:
        required = list(required)
    logger.info("Reindexing %s objects...", total)
    for obj in request.resolve_docids(docids, perm=None):
        cataloger = ICataloger(obj)
        cataloger.index_object(indexes=required)


def _unregister_index_utils(registry=None):
    if registry is None:
        registry = get_current_registry()
    registry.unregisterUtility(provided=ICatalogIndexes)


def includeme(config):
    """ Initialise catalog systems.
    """
    config.registry.registerAdapter(Cataloger, provided=ICataloger)

    config.add_subscriber(index_object_subscriber, [IIndexedContent, IObjectAddedEvent])
    config.add_subscriber(index_object_subscriber, [IIndexedContent, IObjectUpdatedEvent])
    config.add_subscriber(index_object_subscriber, [IIndexedContent, IWorkflowAfterTransition])
    config.add_subscriber(unindex_object_subscriber, [IIndexedContent, IObjectWillBeRemovedEvent])
    config.add_subscriber(check_catalog_on_startup, IApplicationCreated)

    config.add_directive('add_catalog_indexes', add_catalog_indexes)
    config.add_directive('update_index_info', update_index_info)
    config.add_directive('add_searchable_text_index', add_searchable_text_index)
    config.add_directive('add_searchable_text_discriminator', add_searchable_text_discriminator)
    config.add_directive('add_metadata_field', add_metadata_field)
    config.add_directive('create_metadata_field', create_metadata_field)

    config.registry.catalog_indexhelper = CatalogIndexHelper()

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
        'local_roles': CatalogKeywordIndex(get_local_roles),
        'relation': CatalogKeywordIndex(get_relation),
        }
    config.add_catalog_indexes(__name__, default_indexes)
    # Limit these indexes to the User type
    config.update_index_info(('userid', 'email', 'first_name', 'last_name'), type_names = 'User')
    # Force reindex of tags and searchable text every time
    config.update_index_info(('tags', 'searchable_text'), linked=None)
    config.add_searchable_text_index((
        'title',
        'description',
        'body',
        'userid',
        'first_name',
        'last_name',
        'email'
    ))
    config.add_searchable_text_discriminator(_searchable_html_body)
