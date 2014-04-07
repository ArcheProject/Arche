from repoze.folder import Folder
from zope.interface import implementer
#from zope.component import adapter

from arche.interfaces import IBase
from arche.interfaces import IUser
from arche.interfaces import IUsers
from arche.interfaces import IInitialSetup
from arche.utils import hash_method
from arche import _


@implementer(IBase)
class Base(Folder):
    title = u""
    description = u""
    type_name = u""
    type_title = u""
    addable_to = ()
    default_view = u"view"
    nav_visible = True

    def __init__(self, data=None, **kwargs):
        super(Base, self).__init__()
        self.update(**kwargs)

    def update(self, **kwargs):
        for (key, value) in kwargs.items():
            if not hasattr(self, key):
                raise AttributeError("This class doesn't have any '%s' attribute." % key)
            setattr(self, key, value)
        #FIXME event?
        #FIXME: Check current value?


class Document(Base):
    type_name = u"Document"
    type_title = _(u"Document")
    addable_to = (u"Document")


@implementer(IUser)
class User(Base):
    type_name = u"User"
    type_title = _(u"User")
    addable_to = (u'Users')
    first_name = u""
    last_name = u""
    email = u""
    nav_visible = False

    @property
    def title(self):
        return " ".join((self.first_name, self.last_name,)).strip()

    @property
    def userid(self):
        self.__name__

    @property
    def password(self):
        return getattr(self, "__password_hash__", u"")

    @password.setter
    def password(self, value):
        self.__password_hash__ = hash_method(value)


class File(Base):
    pass


class Link(Base):
    pass


class Image(Base):
    pass


@implementer(IInitialSetup)
class InitialSetup(Base):
    type_name = u"InitialSetup"
    type_title = u""
    addable_to = () #Never!
    nav_visible = False
    title = _(u"Welcome to Arche!")
    setup_data = {}


@implementer(IUsers)
class Users(Base):
    type_name = u"Users"
    type_title = _(u"Users")
    addable_to = ()
    nav_visible = False
    title = _(u"Users")


def includeme(config):
    config.add_content_factory(Document)
    config.add_content_factory(Users)
    config.add_content_factory(User)
    config.add_content_factory(InitialSetup)
