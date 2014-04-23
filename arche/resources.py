from repoze.folder import Folder
from zope.interface import implementer
from BTrees.OOBTree import OOSet
from ZODB.blob import Blob
from persistent import Persistent
from pyramid.threadlocal import get_current_registry, get_current_request

from repoze.catalog.catalog import Catalog
from repoze.catalog.document import DocumentMap
from zope.component.event import objectEventNotify

from arche.interfaces import * #Pick later
from arche.utils import hash_method
from arche.utils import upload_stream
from arche.events import ObjectUpdatedEvent
from arche.security import get_local_roles
from arche.security import get_acl_registry
from arche.security import ROLE_OWNER
from arche.catalog import populate_catalog
from arche import _


class DCMetadataMixin(object):
    """ Should always be used as a mixin of another persistent object! """
    title = u""
    description = u""
    creator = None #FIXME
    contributor = u"" #FIXME
    created = None #FIXME
    modified = None #FIXME - also via update?
    date = u""
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


@implementer(IBase)
class BaseMixin(object):
    title = u""
    description = u""
    type_name = u""
    type_title = u""
    type_description = u""
    addable_to = ()

    def __init__(self, **kwargs):
        #IContent should be the same iface registered by the roles adapter
        if 'local_roles' not in kwargs and IContent.providedBy(self):
            #Check creators attribute?
            request = get_current_request()
            userid = getattr(request, 'authenticated_userid', None)
            if userid:
                kwargs['local_roles'] = {userid: [ROLE_OWNER]}
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

    def __init__(self, data=None, **kwargs):
        Folder.__init__(self, data = data)
        super(Content, self).__init__(**kwargs) #BaseMixin!


@implementer(IBare, IIndexedContent)
class Bare(BaseMixin, ContextACLMixin, Persistent):
    __name__ = None
    __parent__ = None
    nav_visible = False
    listing_visible = False

    def __init__(self, data=None, **kwargs):
        #Things like created, creator etc...
        Persistent.__init__(self)
        super(Bare, self).__init__(**kwargs)


@implementer(IRoot, IIndexedContent)
class Root(Content):
    type_name = u"Root"
    type_title = _(u"Site root")
    addable_to = ()
    add_permission = "Add %s" % type_name

    def __init__(self, data=None, **kwargs):
        self.catalog = Catalog()
        self.document_map = DocumentMap()
        populate_catalog(self.catalog)
        reg = get_current_registry()
        cataloger = reg.queryAdapter(self, ICataloger)
        if cataloger: #Not needed for testing
            cataloger.index_object()
        super(Root, self).__init__(data=data, **kwargs)


@implementer(IDocument, IThumbnailedContent)
class Document(Content):
    type_name = u"Document"
    type_title = _(u"Document")
    addable_to = (u"Document", u"Root")
    body = u""
    add_permission = "Add %s" % type_name
    blobfile = None

    @property
    def thumbnail_original(self): return self.blobfile

    @property
    def thumbnail_data(self): pass #FIXME: Should this return something?

    @thumbnail_data.setter
    def thumbnail_data(self, value):
        if value:
            if self.blobfile is None:
                self.blobfile = Blob()
            with self.blobfile.open('w') as f:
                fp = value['fp']
                upload_stream(fp, f)


@implementer(IFile, IContent)
class File(Bare, DCMetadataMixin):
    type_name = u"File"
    type_title = _(u"File")
    addable_to = (u'Document', u"Root")
    add_permission = "Add %s" % type_name
    filename = u""
    blobfile = None
    mimetype = u""
    size = 0

    def __init__(self, file_data, **kwargs):
        self._title = u""
        self.blobfile = Blob()
        super(File, self).__init__(file_data = file_data, **kwargs)

    @property
    def title(self):
        return self._title and self._title or self.filename
    @title.setter
    def title(self, value): self._title = value

    @property
    def file_data(self):
        pass
        #FIXME: Should this return something?

    @file_data.setter
    def file_data(self, value):
        if value:
            with self.blobfile.open('w') as f:
                self.filename = value['filename']
                fp = value['fp']
                self.mimetype = value['mimetype']
                self.size = upload_stream(fp, f)


@implementer(IImage, IThumbnailedContent)
class Image(File):
    type_name = u"Image"
    type_title = _(u"Image")
    addable_to = (u'Document', u"Root")
    add_permission = "Add %s" % type_name
    blobfile = None

    @property
    def thumbnail_original(self):
        return self.blobfile


# class Link(Base):
#     pass
# 
# 

@implementer(IInitialSetup)
class InitialSetup(Bare):
    type_name = u"InitialSetup"
    type_title = _(u"Initial setup")
    addable_to = () #Never!
    nav_visible = False
    title = _(u"Welcome to Arche!")
    setup_data = {}


@implementer(IUsers)
class Users(Content):
    type_name = u"Users"
    type_title = _(u"Users")
    addable_to = ()
    nav_visible = False
    listing_visible = False
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
    addable_to = (u'Users',)
    first_name = u""
    last_name = u""
    email = u""
    add_permission = "Add %s" % type_name
    blobfile = None

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
    def thumbnail_original(self): return self.blobfile

    @property
    def profile_data(self): pass #FIXME: Should this return something?

    @profile_data.setter
    def profile_data(self, value):
        if value:
            if self.blobfile is None:
                self.blobfile = Blob()
            with self.blobfile.open('w') as f:
                #self.filename = value['filename']
                fp = value['fp']
                #self.mimetype = value['mimetype']
                #self.size = upload_stream(fp, f)
                upload_stream(fp, f)

@implementer(IGroups)
class Groups(Content):
    type_name = u"Groups"
    type_title = _(u"Groups")
    addable_to = ()
    nav_visible = False
    listing_visible = False
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
    addable_to = (u'Groups',)
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


def make_user_owner(user, event = None):
    """ Whenever a user object is added, make sure the user has the role owner,
        and no one else. This might not be the default behaviour, if an
        administrator adds the user.
    """
    if ROLE_OWNER not in user.local_roles.get(user.userid, ()):
        user.local_roles = {user.userid: [ROLE_OWNER]}


def includeme(config):
    config.add_content_factory(Document)
    config.add_content_factory(Users)
    config.add_content_factory(User)
    config.add_content_factory(InitialSetup)
    config.add_content_factory(Groups)
    config.add_content_factory(Group)
    config.add_content_factory(File)
    config.add_content_factory(Image)
    config.add_content_factory(Root)
    config.add_subscriber(make_user_owner, [IUser, IObjectAddedEvent])
