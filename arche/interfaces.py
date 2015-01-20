from zope.interface import Interface, Attribute
from zope.component.interfaces import IObjectEvent
from pyramid.interfaces import IDict
from repoze.folder.interfaces import (IObjectAddedEvent,
                                      IObjectWillBeRemovedEvent,
                                      IFolder) #API


#ObjectEvents
class IObjectUpdatedEvent(IObjectEvent):
    pass

class IWorkflowBeforeTransition(IObjectEvent):
    pass

class IWorkflowAfterTransition(IObjectEvent):
    pass

class IViewInitializedEvent(IObjectEvent):
    pass

class ISchemaCreatedEvent(IObjectEvent):
    pass
#/ObjectEvents


#Persistent objects
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

class IWorkflow(Interface):
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
#/Persistent Objects




#Mixin for content objects
class IContextACL(Interface):
    pass

#Markers
class IIndexedContent(Interface):
    """ Marker for content that belongs in catalog.
    """

class IThumbnailedContent(Interface):
    """ Marker for content that could have a thumbnail.
    """
#/Markers


#Views
class IBaseView(Interface):
    """ Marker for more advanced views that inherit BaseView, which should be all view classes.
    """


class IContentView(Interface):
    """ View for content types that have a bit more settings. They're also selectable
        through the action menu if they're registered via the add_content_view method.
    """
    title = Attribute("")
    description = Attribute("")
    settings_schema = Attribute("If this view has settings, this should point to a colander.Schema class or factory.")
    settings = Attribute("Storage for settings. Accepts any dict-like structures.")

#/Views


#Adapters
class IContextAdapter(Interface):
    """ An adapter that wraps a context within the site.
    """
    context = Attribute("The context object that was adapted")

    def __init__(context):
        """ Initialize adapter. """


class IRoles(IContextAdapter):
    """ Adapter for IBase content that stores and fetches assigned roles. """


class ICataloger(IContextAdapter):
    """ Content catalog adapter. """


class IBlobs(IContextAdapter):
    """ Adapter that handles blob storage for a content type.
    """


class IThumbnails(IContextAdapter):
    pass


class IDateTimeHandler(IContextAdapter):
    """ Date time conversion adapter for requests.
    """


class IJSONData(IContextAdapter):
    """ Adapter that pulls json data out of a context object.
    """


class IMetadata(IContextAdapter):
    """ Named adapter that can be registered for objects that should have catalog metadata.
    """
    name = Attribute("Adapter name. Data will be stored with this as key.")

    def __call__(default = None):
        """ Return value to be stored, or default. """


class IPopulator(Interface):
    """ An adapter that populates the database with content or initial setup.
        Should accept root as context.
    """
    def populate(self, **kw):
        """ Populate context with the following arguments. """
#/Adapters


#Utils or settings

class IACLRegistry(Interface):
    pass


class ICatalogIndexes(Interface):
    """ Works as a registry to keep track of all of this or other packages catalog indexes.
    """

    def __call__():
        """ Return a dict where index names are keys and values are the catalog
            index objects that should be stored in the catalog.
        """


#/Utils

class IPortlet(Interface):
    pass

class IPortletType(Interface):
    pass

class IPortletManager(Interface):
    pass

class IFileUploadTempStore(Interface):
    pass

class IRegistrationTokens(Interface):
    pass
