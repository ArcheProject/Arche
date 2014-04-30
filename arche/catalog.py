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


def get_title(context, default): return getattr(context, 'title', default)
def get_description(context, default): return getattr(context, 'description', default)
def get_type_name(context, default): return getattr(context, 'type_name', default)
def get_path(context, default): return resource_path(context)
def get_uid(context, default): return getattr(context, 'uid', default)

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
    #FIXME: Which indexes are searchable?
    searchable_text_discriminators = (get_title, get_description)
    found_text = []
    for discriminator in searchable_text_discriminators:
        res = discriminator(context, default)
        if res is not default and isinstance(res, basestring):
            found_text.append(res.strip())
    text = u" ".join(found_text)
    return text and text or default

def populate_catalog(catalog):
    catalog['title'] = CatalogFieldIndex(get_title)
    catalog['description'] = CatalogFieldIndex(get_description)
    catalog['type_name'] = CatalogFieldIndex(get_type_name)
    catalog['sortable_title'] = CatalogFieldIndex(get_sortable_title)
    catalog['path'] = CatalogPathIndex(get_path)
    lexicon = Lexicon(Splitter(), CaseNormalizer())
    catalog['searchable_text'] = CatalogTextIndex(get_searchable_text, lexicon = lexicon)
    catalog['uid'] = CatalogFieldIndex(get_uid)
    catalog['tags'] = CatalogKeywordIndex(get_tags)

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
    config.add_subscriber(index_object_subscriber, [IIndexedContent, IObjectAddedEvent])
    config.add_subscriber(index_object_subscriber, [IIndexedContent, IObjectUpdatedEvent])
    config.add_subscriber(unindex_object_subscriber, [IIndexedContent, IObjectWillBeRemovedEvent])
