from repoze.folder import Folder
from zope.interface import implementer

from arche.interfaces import IBase
from arche import _


@implementer(IBase)
class Base(Folder):
    title = u""
    description = u""
    type_name = u""
    type_title = u""
    addable_to = ()

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


class File(Base):
    pass


class Link(Base):
    pass


class Image(Base):
    pass


def includeme(config):
    config.add_content_factory(Document)
