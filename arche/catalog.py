from UserDict import IterableUserDict

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


@implementer(ICataloger)
@adapter(IIndexedContent)
class Cataloger(object):

    def __init__(self, context):
        self.context = context
        root = find_root(context)
        self.catalog = root.catalog
        self.document_map = root.document_map
        self.index_registry = get_index_registry()
        if self.index_registry.checked == False:
            self.init()
        self.path = resource_path(self.context)

    def init(self):
        for (name, index) in self.index_registry.items():
            if name not in self.catalog:
                #FIXME Discriminator?
                #FIXME Other kw args?
                self.catalog[name] = index
        #to remove
        for key in set(self.catalog.keys()) - set(self.index_registry.keys()):
            del self.catalog[key]
        self.index_registry.checked = True

    def index_object(self):
        docid = self.document_map.docid_for_address(self.path)
        if docid is None:
            docid = self.document_map.add(self.path)
            self.catalog.reindex_doc(docid, self.context)
        else:
            self.catalog.index_doc(docid, self.context)

    def unindex_object(self):
        docid = self.document_map.docid_for_address(self.path)
        if docid is not None:
            self.catalog.unindex_doc(docid)
            self.document_map.remove_address(self.path)

    def rebuild_catalog(self):
        ###FIXME Find all objects in database and reindex them
        pass


class CatalogIndexes(IterableUserDict):
    checked = False
    searchable_text = {}


def add_catalog_index(config, name, index):
    indexer_reg = get_index_registry(config.registry)
    indexer_reg[name] = index

def get_index_registry(registry=None):
    if registry is None:
        registry = get_current_registry()
    return registry._catalog_indexes

def add_default_indexes(config):
    indexer_reg = get_index_registry(config.registry)
    #Default regular attribute indexers
    #Title
    def get_title(context, default): return getattr(context, 'title', default)
    config.add_catalog_index('title', CatalogFieldIndex(get_title))
    indexer_reg.searchable_text['title'] = get_title
    #description
    def get_description(context, default): return getattr(context, 'description', default)
    config.add_catalog_index('description', CatalogFieldIndex(get_description))
    indexer_reg.searchable_text['description'] = get_description
    #type_name
    def get_type_name(context, default): return getattr(context, 'type_name', default)
    config.add_catalog_index('type_name', CatalogFieldIndex(get_type_name))
    #FIXME: Body + strip html
    #sortable title
    def get_sortable_title(context, default):
        title = getattr(context, 'title', default)
        return title and title.lower() or default
    config.add_catalog_index('sortable_title', CatalogFieldIndex(get_sortable_title))
    #userid
    def get_userid(context, default):
        if IUser.providedBy(context):
            return context.userid and context.userid or default
        return default
    config.add_catalog_index('userid', CatalogFieldIndex(get_userid))
    indexer_reg.searchable_text['userid'] = get_userid
    #Searchable text
    def _searchable_text_discriminator(context, default):
        indexer_reg = get_index_registry()
        found_text = []
        for discriminator in indexer_reg.searchable_text.values():
            res = discriminator(context, default)
            if res is not default and isinstance(res, basestring):
                found_text.append(res.strip())
        text = u" ".join(found_text)
        return text and text or default
    lexicon = Lexicon(Splitter(), CaseNormalizer())
    searchable_text_index = CatalogTextIndex(_searchable_text_discriminator, lexicon = lexicon)
    config.add_catalog_index('searchable_text', searchable_text_index)


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


def includeme(config):
    config.registry.registerAdapter(Cataloger)
    config.add_directive('add_catalog_index', add_catalog_index)
    config.registry._catalog_indexes = CatalogIndexes()
    add_default_indexes(config)
    config.add_subscriber(index_object_subscriber, [IIndexedContent, IObjectAddedEvent])
    config.add_subscriber(index_object_subscriber, [IIndexedContent, IObjectUpdatedEvent])
    config.add_subscriber(unindex_object_subscriber, [IIndexedContent, IObjectWillBeRemovedEvent])
