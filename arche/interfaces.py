from zope.interface import Interface, Attribute
from zope.component.interfaces import IObjectEvent

from repoze.folder.interfaces import (IObjectAddedEvent,
                                      IObjectWillBeRemovedEvent,
                                      IFolder) #API

class IObjectUpdatedEvent(IObjectEvent):
    pass


class IBase(Interface):
    pass

class IBare(Interface):
    pass

class IContent(Interface):
    pass

class IDocument(Interface):
    pass

class IUser(IBase):
    pass

class IUsers(Interface):
    pass

class IFile(Interface):
    pass

class IImage(Interface):
    pass

class IFlashMessages(Interface):
    pass

class IRoot(Interface):
    """ Marker interface for the site root."""

class IInitialSetup(Interface):
    """ For populating the site."""

class IGroup(Interface):
    pass

class IGroups(Interface):
    pass

class IRole(Interface):
    pass

class IRoles(Interface):
    """ Adapter for IBase content that stores and fetches assigned roles. """

class ICataloger(Interface):
    """ Content catalog adapter. """

class IIndexedContent(Interface):
    """ Marker for content that belongs in catalog.
    """

class IThumbnailedContent(Interface):
    """ Marker for content that could have a thumbnail.
    """
    thumbnail_original = Attribute("A non-opened data stream like a blobfile. It should support the same functions as an StringIO.")

class IThumbnails(Interface):
    pass

class IPortlet(Interface):
    pass

class IPortletType(Interface):
    pass

class IPortletManager(Interface):
    pass

class IPopulator(Interface):
    """ An adapter that populates the database with content or initial setup.
        Should accept root as context.
    """
    def populate(self, **kw):
        """ Populate context with the following arguments. """
