from zope.interface import Interface
from zope.component.interfaces import IObjectEvent

from repoze.folder.interfaces import (IObjectAddedEvent,
                                      IObjectWillBeRemovedEvent) #API

class IObjectUpdatedEvent(IObjectEvent):
    pass


class IBase(Interface):
    pass

class IBare(Interface):
    pass

class IContent(Interface):
    pass

class IUser(IBase):
    pass

class IUsers(Interface):
    pass

class IFile(Interface):
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

class IPortlet(Interface):
    pass

class IPortletType(Interface):
    pass

class IPortletManager(Interface):
    pass
