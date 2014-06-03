from datetime import timedelta
from random import choice
from uuid import uuid4
import string

from BTrees.OOBTree import OOBTree
from BTrees.OOBTree import OOSet
from persistent import Persistent
from persistent.list import PersistentList
from pyramid.threadlocal import get_current_registry
from pyramid.threadlocal import get_current_request
from repoze.catalog.catalog import Catalog
from repoze.catalog.document import DocumentMap
from repoze.folder import Folder
from zope.component.event import objectEventNotify
from zope.interface import implementer
import requests

from arche import _
from arche.catalog import populate_catalog
from arche.events import ObjectUpdatedEvent
from arche.interfaces import *  # Pick later
from arche.security import ROLE_OWNER
from arche.security import get_acl_registry
from arche.security import get_local_roles
from arche.utils import hash_method
from arche.utils import remote_cache
from arche.utils import utcnow


class DCMetadataMixin(object):
    """ Should always be used as a mixin of another persistent object! """
    title = u""
    description = u""
    created = None #FIXME
    modified = None #FIXME - also via update?
    date = None
    publisher = u""
    subject = u"" #FIXME: Same as tags?
    relation = u"" #Probably a  relation field here
    rights = u"" #FIXME: global default is a good idea
    
    #type = u"" #FIXME?
    format = u"" #Mimetype or similar?
    source = u"" #Sources?

    @property
    def identifier(self):
        return self.request.resource_url(self.context)

    @property
    def contributor(self): return getattr(self, '__contributor__', ())
    @contributor.setter
    def contributor(self, value):
        if value:
            self.__contributor__ = PersistentList(value)
        else:
            if hasattr(self, '__contributor__'):
                delattr(self, '__contributor__')

    @property
    def creator(self): return getattr(self, '__creator__', ())
    @creator.setter
    def creator(self, value):
        if value:
            self.__creator__ = PersistentList(value)
        else:
            if hasattr(self, '__creator__'):
                delattr(self, '__creator__')

    @property
    def relation(self):
        return getattr(self, '__relation__', ())
    
    @relation.setter
    def relation(self, value):
        if value:
            self.__relation__ = PersistentList(value)
        else:
            if hasattr(self, '__relation__'):
                delattr(self, '__relation__')


@implementer(IBase)
class BaseMixin(object):
    title = u""
    description = u""
    type_name = u""
    type_title = u""
    type_description = u""
    uid = None

    def __init__(self, **kwargs):
        #IContent should be the same iface registered by the roles adapter
        request = get_current_request()
        if 'local_roles' not in kwargs and IContent.providedBy(self):
            #Check creators attribute?
            userid = getattr(request, 'authenticated_userid', None)
            if userid:
                kwargs['local_roles'] = {userid: [ROLE_OWNER]}
        if 'uid' not in kwargs:
            kwargs['uid'] = unicode(uuid4())
        if 'created' not in kwargs and hasattr(self, 'created'):
            kwargs['created'] = utcnow()
        self.update(event = False, **kwargs)

    def update(self, event = True, **kwargs):
        _marker = object()
        changed_attributes = set()
        for (key, value) in kwargs.items():
            if not hasattr(self, key):
                raise AttributeError("This class doesn't have any '%s' attribute." % key)
            if getattr(self, key, _marker) != value:
                setattr(self, key, value)
                changed_attributes.add(key)
        if hasattr(self, 'modified') and 'modified' not in kwargs and changed_attributes:
            self.modified = utcnow()
            changed_attributes.add('modified')
        if event:
            event_obj = ObjectUpdatedEvent(self, changed = changed_attributes)
            objectEventNotify(event_obj)
        return changed_attributes

    @property
    def local_roles(self): return get_local_roles(self)

    @local_roles.setter
    def local_roles(self, value):
        #Note that you can also set roles via the property, like self.local_roles['admin'] = ['role:Admin']
        local_roles = get_local_roles(self)
        local_roles.set_from_appstruct(value)

    @property
    def tags(self): return getattr(self, '__tags__', ())
    @tags.setter
    def tags(self, value):
        #Is this the right way to mutate objects, or should we simply clear the contents?
        if value:
            self.__tags__ = OOSet(value)
        else:
            if hasattr(self, '__tags__'):
                delattr(self, '__tags__')


class ContextACLMixin(object):

    @property
    def __acl__(self):
        acl_reg = get_acl_registry()
        return acl_reg.get_acl(self.type_name) #FIXME wf here


@implementer(IContent, IIndexedContent)
class Content(BaseMixin, Folder, ContextACLMixin, DCMetadataMixin):
    default_view = u"view"
    nav_visible = True
    listing_visible = True
    search_visible = True
    show_byline = False
    related_content = None

    def __init__(self, data=None, **kwargs):
        Folder.__init__(self, data = data)
        super(Content, self).__init__(**kwargs) #BaseMixin!


@implementer(IBare, IIndexedContent)
class Bare(BaseMixin, ContextACLMixin, Persistent):
    __name__ = None
    __parent__ = None
    nav_visible = False
    listing_visible = False
    search_visible = False
    created = None

    def __init__(self, data=None, **kwargs):
        #Things like created, creator etc...
        Persistent.__init__(self)
        super(Bare, self).__init__(**kwargs)


@implementer(ILink)
class Link(Bare):
    """ A persistent way of redirecting somewhere. """
    type_name = u"Link"
    type_title = _(u"Link")
    type_description = _(u"Content type that redirects to somewhere.")
    add_permission = "Add %s" % type_name
    target = u""


@implementer(IExternalResource)
class ExternalResource(Bare):
    type_name = u"ExternalResource"
    type_title = _(u"External Resource")
    type_description = _(u"Some kind of external resource.")
    add_permission = "Add %s" % type_name
    target = u""

    @property
    def data(self):
        if self.target:
            data = remote_cache.get(self.target, None)
            if data is not None:
                return data
            response = requests.get(self.target, verify = False)
            if response.ok:
                data = response.json()
                remote_cache.put(self.target, data)
                return data
        return {}

    @property
    def title(self):
        return self.data.get('title', u'')



@implementer(IRoot, IIndexedContent)
class Root(Content):
    type_name = u"Root"
    type_title = _(u"Site root")
    add_permission = "Add %s" % type_name
    search_visible = False

    def __init__(self, data=None, **kwargs):
        self.catalog = Catalog()
        self.document_map = DocumentMap()
        populate_catalog(self.catalog)
        reg = get_current_registry()
        cataloger = reg.queryAdapter(self, ICataloger)
        if cataloger: #Not needed for testing
            cataloger.index_object()
        self.__site_settings__ = OOBTree()
        super(Root, self).__init__(data=data, **kwargs)

    @property
    def site_settings(self): return getattr(self, '__site_settings__', {})
    @site_settings.setter
    def site_settings(self, value):
        self.__site_settings__.clear()
        self.__site_settings__.update(value)


@implementer(IDocument, IThumbnailedContent)
class Document(Content):
    type_name = u"Document"
    type_title = _(u"Document")
    body = u""
    add_permission = "Add %s" % type_name

    @property
    def image_data(self): pass #FIXME: Should this return something?
    @image_data.setter
    def image_data(self, value):
        IBlobs(self).create_from_formdata('image', value)


@implementer(IFile, IContent)
class File(Bare, DCMetadataMixin):
    type_name = u"File"
    type_title = _(u"File")
    add_permission = "Add %s" % type_name
    filename = u""
    mimetype = u""
    size = 0
    blob_key = "file"

    def __init__(self, file_data, **kwargs):
        self._title = u""
        super(File, self).__init__(file_data = file_data, **kwargs)

    @property
    def title(self):
        return self._title and self._title or self.filename
    @title.setter
    def title(self, value): self._title = value

    @property
    def file_data(self): pass #FIXME: Should this return something?
    @file_data.setter
    def file_data(self, value):
        IBlobs(self).create_from_formdata(self.blob_key, value)

    @property
    def filename(self):
        blobs = IBlobs(self)
        return self.blob_key in blobs and blobs[self.blob_key].filename or u""

    @property
    def mimetype(self):
        blobs = IBlobs(self)
        return self.blob_key in blobs and blobs[self.blob_key].mimetype or u""

    @property
    def size(self):
        blobs = IBlobs(self)
        return self.blob_key in blobs and blobs[self.blob_key].size or u""


@implementer(IImage, IContent, IThumbnailedContent)
class Image(File):
    type_name = u"Image"
    type_title = _(u"Image")
    add_permission = "Add %s" % type_name
    blob_key = "file"


@implementer(IInitialSetup)
class InitialSetup(Bare):
    type_name = u"InitialSetup"
    type_title = _(u"Initial setup")
    nav_visible = False
    search_visible = False
    title = _(u"Welcome to Arche!")
    setup_data = {}


@implementer(IUsers)
class Users(Content):
    type_name = u"Users"
    type_title = _(u"Users")
    nav_visible = False
    listing_visible = False
    search_visible = False
    title = _(u"Users")

    def get_user_by_email(self, email, default = None):
        #FIXME use catalog instead?
        for user in self.values():
            if email == user.email:
                return user


@implementer(IUser, IThumbnailedContent, IContent)
class User(Bare):
    type_name = u"User"
    type_title = _(u"User")
    first_name = u""
    last_name = u""
    email = u""
    add_permission = "Add %s" % type_name
    pw_token = None

    @property
    def title(self):
        title = " ".join((self.first_name, self.last_name,)).strip()
        return title and title or self.userid

    @property
    def userid(self): return self.__name__

    @property
    def password(self): return getattr(self, "__password_hash__", u"")
    @password.setter
    def password(self, value): self.__password_hash__ = hash_method(value)

    @property
    def image_data(self): pass #FIXME: Should this return something?
    @image_data.setter
    def image_data(self, value):
        IBlobs(self).create_from_formdata('image', value)


@implementer(IGroups)
class Groups(Content):
    type_name = u"Groups"
    type_title = _(u"Groups")
    nav_visible = False
    listing_visible = False
    search_visible = False
    title = _(u"Groups")

    def get_users_group_principals(self, userid):
        #Cache memberships? Needed on sites with many groups
        groups = set()
        for group in self.values():
            if userid in group.members:
                groups.add(group.principal_name)
        return groups

    def get_group_principals(self):
        for group in self.values():
            yield group.principal_name


@implementer(IGroup)
class Group(Bare):
    type_name = u"Group"
    type_title = _(u"Group")
    add_permission = "Add %s" % type_name
    title = u""
    description = u""

    def __init__(self, **kwargs):
        #Things like created, creator etc...
        super(Group, self).__init__()
        self.__members__ = OOSet()
        self.update(event = False, **kwargs)

    @property
    def principal_name(self):
        """ The way the security system likes to check names
            to avoid collisions with userids.
        """
        return u"group:%s" % self.__name__

    @property
    def members(self):
        return self.__members__

    @members.setter
    def members(self, value):
        self.__members__.clear()
        self.__members__.update(value)


@implementer(IToken)
class Token(Persistent):
    data = ""
    created = None
    expires = None
    type_name = u"Token"
    type_tile = _(u"Token")

    def __init__(self, size = 40, hours = 3):
        super(Token, self).__init__()
        self.data = u''.join([choice(string.letters + string.digits) for x in range(size)])
        self.created = utcnow()
        self.expires = self.created + timedelta(hours = hours)

    def __eq__(self, other): return other == self.data
    def __repr__(self): return self.data

    @property
    def valid(self):
        return utcnow() < self.expires


def make_user_owner(user, event = None):
    """ Whenever a user object is added, make sure the user has the role owner,
        and no one else. This might not be the default behaviour, if an
        administrator adds the user.
    """
    if ROLE_OWNER not in user.local_roles.get(user.userid, ()):
        user.local_roles = {user.userid: [ROLE_OWNER]}


def includeme(config):
    config.add_content_factory(Document)
    config.add_addable_content('Document', ('Document', 'Root'))
    config.add_content_factory(Users)
    config.add_content_factory(User)
    config.add_addable_content('User', 'Users')
    config.add_content_factory(InitialSetup)
    config.add_content_factory(Groups)
    config.add_content_factory(Group)
    config.add_addable_content('Group', 'Groups')
    config.add_content_factory(File)
    config.add_addable_content('File', ('Root', 'Document'))
    config.add_content_factory(Image)
    config.add_addable_content('Image', ('Root', 'Document'))
    config.add_content_factory(Root)
    config.add_content_factory(Link)
    config.add_addable_content('Link', ('Root', 'Document'))
    config.add_content_factory(ExternalResource)
    config.add_addable_content('ExternalResource', ('Root', 'Document'))
    config.add_content_factory(Token)
    config.add_subscriber(make_user_owner, [IUser, IObjectAddedEvent])
