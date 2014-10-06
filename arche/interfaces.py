from zope.interface import Interface, Attribute
from zope.component.interfaces import IObjectEvent

from repoze.folder.interfaces import (IObjectAddedEvent,
                                      IObjectWillBeRemovedEvent,
                                      IFolder) #API

class IObjectUpdatedEvent(IObjectEvent):
    pass

class IViewInitializedEvent(IObjectEvent):
    pass

class IBase(Interface):
    pass

class ILocalRoles(Interface):
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

class ILink(Interface):
    pass

class IToken(Interface):
    pass

class IRoles(Interface):
    """ Adapter for IBase content that stores and fetches assigned roles. """

class ICataloger(Interface):
    """ Content catalog adapter. """

class IIndexedContent(Interface):
    """ Marker for content that belongs in catalog.
    """

class IBaseView(Interface):
    """ Marker for more advanced views that inherit BaseView, which should be all view classes.
    """

class IThumbnailedContent(Interface):
    """ Marker for content that could have a thumbnail.
    """


class IBlobs(Interface):
    """ Adapter that handles blob storage for a content type.
    """

class IThumbnails(Interface):
    pass

class IPortlet(Interface):
    pass

class IPortletType(Interface):
    pass

class IPortletManager(Interface):
    pass

class IDateTimeHandler(Interface):
    """ Date time conversion adapter for requests.
    """

class IRegistrationTokens(Interface):
    pass

class IPopulator(Interface):
    """ An adapter that populates the database with content or initial setup.
        Should accept root as context.
    """
    def populate(self, **kw):
        """ Populate context with the following arguments. """


class IContentView(Interface):
    """ View for content types that have a bit more settings. They're also selectable
        through the action menu if they're registered via the add_content_view method.
    """
    title = Attribute("")
    description = Attribute("")
    settings_schema = Attribute("If this view has settings, this should point to a colander.Schema class or factory.")
    settings = Attribute("Storage for settings. Accepts any dict-like structures.")
