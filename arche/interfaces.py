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
    type_name = Attribute("String: Internal content type name. Usually same as class.")
    type_title = Attribute("Strig: Readable type name, displayed to users.")
    type_description = Attribute("String: Readable description of this content type.")
    uid = Attribute("String: Globally unique id.")
    created = Attribute("DateTime: When the object was created. Always saved in UTC timezone.")
    nav_visible = Attribute("Bool: Should it be visible in navigation-like structures?")
    listing_visible = Attribute("Bool: Should it be visible in lising-like structures?")
    search_visible = Attribute("Bool: Included in search results?")
    show_byline = Attribute("Bool: Display a byline for this content type, if applicable.")
    naming_attr = Attribute("String: Attribute used to figure out a name (for the URL) for this content. "
                            "'title' is a good choice for public things and 'uid' for internal "
                            "things that shouldn't be accessible directly.")

    def update(event = True, **kwargs):
        """ Update values
            will also make sure that any keys exist as attributes on this object.
            If event is true an IObjectUpdatedEvent will be sent.
            It's a good idea not to send this if the object hasn't been attached to the
            resource tree yet.
        """

class ILocalRoles(Interface):
    pass

class IContent(Interface):
    pass

class IDocument(Interface):
    pass

class IUser(IBase):
    first_name = Attribute("First name")
    last_name = Attribute("Last name")
    email =  Attribute("Email")
    pw_token =  Attribute("Will access a password reset token if that process was initiated.")
    email_validated = Attribute("Is the current email address validated?")
    userid = Attribute("Same as __name__ for user objects. Contains UserID.")
    password = Attribute("Getter and setter for password. Note that it will be hashed.")
    timezone = Attribute("Getter an setter for timezone.")


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

class IEmailValidationTokens(Interface):
    pass
