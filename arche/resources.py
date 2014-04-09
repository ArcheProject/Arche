from repoze.folder import Folder
from zope.interface import implementer
from BTrees.OOBTree import OOSet
from persistent import Persistent
#from zope.component import adapter

from arche.interfaces import IBase
from arche.interfaces import IBare
from arche.interfaces import IContent
from arche.interfaces import IUser
from arche.interfaces import IUsers
from arche.interfaces import IGroup
from arche.interfaces import IGroups
from arche.interfaces import IInitialSetup
from arche.utils import hash_method
from arche.security import get_default_acl, get_local_roles
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

    def update(self, **kwargs):
        for (key, value) in kwargs.items():
            if not hasattr(self, key):
                raise AttributeError("This class doesn't have any '%s' attribute." % key)
            setattr(self, key, value)
        #FIXME event?
        #FIXME: Check current value?


class ContextRolesMixin(object):

    @property
    def roles(self):
        return get_local_roles(self)

    #Roles to own type?
    #FIXME: When the view will be rewritten, this attr goes...
    @property
    def local_roles(self):
        local_roles = get_local_roles(self)
        return local_roles.get_appstruct()

    @local_roles.setter
    def local_roles(self, value):
        local_roles = get_local_roles(self)
        local_roles.set_from_appstruct(value)


@implementer(IContent)
class Content(BaseMixin, Folder, ContextRolesMixin, DCMetadataMixin):
    default_view = u"view"
    nav_visible = True
    listing_visible = True

    def __init__(self, data=None, **kwargs):
        #Things like created, creator etc...
        Folder.__init__(self, data = data)
        self.update(**kwargs)


@implementer(IBare)
class Bare(BaseMixin, Persistent):
    __name__ = None
    __parent__ = None

    def __init__(self, data=None, **kwargs):
        #Things like created, creator etc...
        Persistent.__init__(self)
        self.update(**kwargs)

    def update(self, **kwargs):
        for (key, value) in kwargs.items():
            if not hasattr(self, key):
                raise AttributeError("This class doesn't have any '%s' attribute." % key)
            setattr(self, key, value)


class Document(Content):
    type_name = u"Document"
    type_title = _(u"Document")
    addable_to = (u"Document")
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
        return " ".join((self.first_name, self.last_name,)).strip()

    @property
    def userid(self):
        return self.__name__

    @property
    def password(self):
        return getattr(self, "__password_hash__", u"")

    @password.setter
    def password(self, value):
        self.__password_hash__ = hash_method(value)


# class File(Base):
#     pass
# 
# 
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
