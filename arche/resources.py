from repoze.folder import Folder
from zope.interface import implementer
from BTrees.OOBTree import OOSet
from ZODB.blob import Blob
from persistent import Persistent
from pyramid.threadlocal import get_current_registry
#from zope.component import adapter
from repoze.catalog.catalog import Catalog
from repoze.catalog.document import DocumentMap
from zope.component.event import objectEventNotify

from arche.interfaces import IBase
from arche.interfaces import IBare
from arche.interfaces import IRoot
from arche.interfaces import IContent
from arche.interfaces import IFile
from arche.interfaces import IUser
from arche.interfaces import IUsers
from arche.interfaces import IGroup
from arche.interfaces import IGroups
from arche.interfaces import IInitialSetup
from arche.interfaces import IIndexedContent
from arche.interfaces import ICataloger
from arche.utils import hash_method
from arche.utils import upload_stream
from arche.events import ObjectUpdatedEvent
from arche.security import get_default_acl, get_local_roles
from arche.catalog import populate_catalog
from arche import _


class DCMetadataMixin(object):
    """ Should always be used as a mixin of another persistent object! """
    title = u""
    description = u""
    creator = u"" #FIXME
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
    addable_to = ()

    @property
    def __acl__(self):
        return get_default_acl()

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
        #FIXME event?
        #FIXME: Check if value should be removed?
        #


class ContextRolesMixin(object):

    @property
    def local_roles(self): return get_local_roles(self)

    @local_roles.setter
    def local_roles(self, value):
        local_roles = get_local_roles(self)
        local_roles.set_from_appstruct(value)


@implementer(IContent, IIndexedContent)
class Content(BaseMixin, Folder, ContextRolesMixin, DCMetadataMixin):
    default_view = u"view"
    nav_visible = True
    listing_visible = True

    def __init__(self, data=None, **kwargs):
        #Things like created, creator etc...
        Folder.__init__(self, data = data)
        self.update(event = False, **kwargs)


@implementer(IBare, IIndexedContent)
class Bare(BaseMixin, Persistent):
    __name__ = None
    __parent__ = None

    def __init__(self, data=None, **kwargs):
        #Things like created, creator etc...
        Persistent.__init__(self)
        self.update(event = False, **kwargs)


@implementer(IRoot, IIndexedContent)
class Root(Content):
    type_name = u"Root"
    type_title = _(u"Site root")
    addable_to = ()
    
    def __init__(self, data=None, **kwargs):
        self.catalog = Catalog()
        self.document_map = DocumentMap()
        populate_catalog(self.catalog)
        reg = get_current_registry()
        cataloger = reg.getAdapter(self, ICataloger)
        cataloger.index_object()
        super(Root, self).__init__(data=data, **kwargs)


class Document(Content):
    type_name = u"Document"
    type_title = _(u"Document")
    addable_to = (u"Document", u"Root")
    body = u""


@implementer(IUser)
class User(Bare):
    type_name = u"User"
    type_title = _(u"User")
    addable_to = (u'Users')
    first_name = u""
    last_name = u""
    email = u""

    @property
    def title(self):
        title = " ".join((self.first_name, self.last_name,)).strip()
        return title and title or self.userid

    @property
    def userid(self): return self.__name__

    @property
    def password(self): return getattr(self, "__password_hash__", u"")

    @password.setter
    def password(self, value):
        self.__password_hash__ = hash_method(value)


@implementer(IFile)
class File(Bare):
    type_name = u"File"
    type_title = _(u"File")
    addable_to = (u'Document', u"Root")
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
            self.filename = value['filename']
            fp = value['fp']
            self.mimetype = value['mimetype']
            f = self.blobfile.open('w')
            self.size = upload_stream(fp, f)
            f.close()

# class Link(Base):
#     pass
# 
# 
# class Image(Base):
#     pass


@implementer(IInitialSetup)
class InitialSetup(Bare):
    type_name = u"InitialSetup"
    type_title = u""
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


@implementer(IGroups)
class Groups(Content):
    type_name = u"Groups"
    type_title = _(u"Groups")
    addable_to = ()
    nav_visible = False
    listing_visible = False
    title = _(u"Groups")

    def get_groups_roles_security(self, userid):
        #Cache memberships? Needed on sites with many groups
        groups = set()
        roles = set()
        for group in self.values():
            if userid in group.members:
                groups.add(group.principal_name)
                roles.update(group.roles)
        return groups, roles

    def get_group_principals(self):
        for group in self.values():
            yield group.principal_name


@implementer(IGroup)
class Group(Bare):
    type_name = u"Group"
    type_title = _(u"Group")
    addable_to = (u'Groups')
    title = u""
    description = u""

    def __init__(self, **kwargs):
        #Things like created, creator etc...
        super(Group, self).__init__()
        self.__members__ = OOSet()
        self.__roles__ = OOSet()
        self.update(**kwargs)

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

    #FIXME: Remove the whole concept of group roles.
    #They can be assigned in the root instead
    #This just makes it more confusing
    @property
    def roles(self):
        return self.__roles__

    @roles.setter
    def roles(self, value):
        self.__roles__.clear()
        self.__roles__.update(value)


def includeme(config):
    config.add_content_factory(Document)
    config.add_content_factory(Users)
    config.add_content_factory(User)
    config.add_content_factory(InitialSetup)
    config.add_content_factory(Groups)
    config.add_content_factory(Group)
    config.add_content_factory(File)
    config.add_content_factory(Root)
