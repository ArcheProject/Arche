from zope.interface import Interface, Attribute
from zope.component.interfaces import IObjectEvent
from pyramid.interfaces import IDict
from repoze.folder.interfaces import (IObjectWillBeAddedEvent,
                                      IObjectAddedEvent,
                                      IObjectWillBeRemovedEvent,
                                      IObjectRemovedEvent,
                                      IFolder) #API

#Base classes
class IImmutableDict(Interface):
    """ A dict-like interface that isn't ment to be changed like a dictionary.
    """

    def __contains__(k):
        """ Return ``True`` if key ``k`` exists in the dictionary."""

    def __getitem__(k):
        """ Return the value for key ``k`` from the dictionary or raise a
        KeyError if the key doesn't exist"""

    def __iter__():
        """ Return an iterator over the keys of this dictionary """

    def get(k, default=None):
        """ Return the value for key ``k`` from the renderer dictionary, or
        the default if no such value exists."""

    def items():
        """ Return a list of [(k,v)] pairs from the dictionary """

    def keys():
        """ Return a list of keys from the dictionary """

    def values():
        """ Return a list of values from the dictionary """
#/Base classes


#Regular events
class IWillLoginEvent(Interface):
    """ Event that fires after a user has passed all credential checks,
        or registered and is about to receive a redirect with headers to authenticate.
        
        Note: The user is still counted as anonymous!
    """
    user = Attribute("The user object")
    request = Attribute("Current request, remember that request.authenticated_userid won't work!")
    first_login = Attribute("First login since registration?")


class IEmailValidatedEvent(Interface):
    """ A users email address was just validated.
        The event is for User objects, but won't fire unless the object is attached to the resource tree.
        It will fire when a User object is attached for the first time though.
    """
    user = Attribute("User profile for the email address.")
#/Regular events


#ObjectEvents
class IObjectUpdatedEvent(IObjectEvent):
    pass


class IWorkflowTransition(IObjectEvent):
    """ Base class for transitions.
        Should normally not be used unless you want something to fire
        both before and after a transition, since
        IWorkflowBeforeTransition and IWorkflowAfterTransition inherits this.
    """
    object = Attribute("The object which the transition occurs on, normally a resource or context.")
    workflow = Attribute("Registered workflow")
    transition = Attribute("The transition object")
    request = Attribute("Current request")
    to_state = Attribute("The state the object transitions to.")
    from_state = Attribute("The state the object transitions from.")


class IWorkflowBeforeTransition(IWorkflowTransition):
    """ Fires before a transition takes place. """


class IWorkflowAfterTransition(IWorkflowTransition):
    """ Fires after a transition takes place. """


class IViewInitializedEvent(IObjectEvent):
    """ A view class has been initialized with context and request.
    """
    object = Attribute("The instantiated view.")


class ISchemaCreatedEvent(IObjectEvent):
    pass

class IFormSuccessEvent(IObjectEvent):
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

class ILocalRoles(IDict):

    def add(key, value):
        """
        Append one or more roles.

        :param key: principal (usually userid or group) to add roles to
        :type key: str
        :param value: Role or roles to add
        :type value: iterable, role or string.
        """

    def remove(key, value):
        """
        Remove one or more roles. If all roles have been removed, the key will be removed too.

        :param key: principal (usually userid or group) to remove roles from
        :type key: str
        :param value: Role or roles to remove
        :type value: iterable, role or string.
        """

    def set_from_appstruct(value):
        """
        Set local roles to value, where value must be a dict with principal as key and roles as values.
        Will clear any keys not present in value.
        """

    def get_any_local_with(role):
        """
        Fetch any local principals with the assigned role.

        :returns: Generator
        """

    def get_assignable(registry = None):
        """
        Return any roles that might be assignable in this context.
        Will first check if assignable is True and after that check if required is set to any interfaces.
        If so, check the interfaces against the current context.

        :returns: Dict with role name as key and role as value.
        """


class IContent(Interface):
    pass

class IDocument(Interface):
    pass

class IArcheFolder(IContent):
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
    """ A folder containing all users. """

    def get_user_by_email(email, default = None, only_validated = False):
        """ Get a user object by email address regardless of permissions.
            Used by validators, login etc.
            
            If only_validated is True, only return a hit if the users email
            address has been validated.
        """


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
    """ Groups container"""

    def get_users_group_principals(userid):
        """ Get principal name (I.e. what a permission will be attached to)
            Will always start with 'group:'
        """

    def get_users_groups(userid):
        """ Return a generator with all the groups where userid is a member.
        """

    def get_group_principals(self):
        """ Return a set with all the principal names of the registered groups.
        """


class IRole(Interface):
    pass

class ILink(Interface):
    pass

class IToken(Interface):
    pass
#/Persistent Objects


#Mixin for content objects
class IContextACL(Interface):
    """ Mixin for content that cares about security in some way. Could either be workflows or ACL.
        If the __acl__ attribute isn't provided for objects, Pyramids default behaviour is to inherit from the parent object.
    """
    __acl__ = Attribute("Returns ACL structure. Workflows have presidence over "
                        "ACL registries with the same name as the type_name. "
                        "If nothing can be found, the 'default' acl registry is returned.")
    workflow = Attribute("Get the assigned workflow (an adapter) if any.")
    wf_state = Attribute("Get the workflow state id or None. "
                         "If an invalid state ID is set, the default state for the "
                         "workflow will be returned.")

#Markers
class IIndexedContent(Interface):
    """ Marker for content that belongs in catalog.
    """

class IThumbnailedContent(Interface):
    """ Marker for content that could have a thumbnail.
    """
    blob_key = Attribute("Where the blob for the thumbnail will be stored. "
                         "For images and files, it's usually 'file'")

class ITrackRevisions(Interface):
    """ Marker interface for content that could keep track of revisions.
    """
#/Markers


#Views
class IBaseView(Interface):
    """ Marker for more advanced views that inherit BaseView, which should be all view classes.
    """


class IBaseForm(IBaseView):
    """ Marker for base form views.
    """


class IAPIKeyView(Interface):
    """ Marker indicates that this view can be accessed remotely by using API keys.
        It doesn't define guards or similar, it simply states that it's allowed.
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


class IRoles(IContextAdapter, IDict):
    """ Adapter for IBase content that stores and fetches assigned roles.
        Works like a dict where the key is the principal (userid, group etc)
        you wish to assign roles to, and values are roles.
        
        It also has some extra methods described below.
    """

    def add(key, value):
        """ Add role/roles to a principal(key). It will keep the previous roles.
        """

    def remove(key, value):
        """ Remove role/roles from a principal. Any other roles not specified will be kept.
            If all roles are removed by this action, the key will be removed too.
            
            It will not raise errors if the role you're trying to remove doesn't exist.
        """

    def set_from_appstruct(value):
        """ Sets the local roles exactly as specified. value must be a dict here.
            Note that any keys not present in the dict will be cleared
            so be careful when using this.
        """


class IRolesCommitLogger(Interface):
    """ Stores role changes that was actually committed to the database.
        Saves in json format, so it's easier to parse and extract specific contexts.
    """
    request = Attribute("Webob request")
    logger = Attribute(
        "The logging facility. It will log to a namespace outside of arche to make sure "
        "it doesn't propagate to the regular logger. "
        "(Since it logs json, this would be a bad idea)")
    loglvl = Attribute("Default level to send")
    attached = Attribute("Is it hooked to the transaction?")

    def __init__(request):
        """ Initalize adapter. """

    def add(uid, key, new, old):
        """ Append to entries. This should be handled at the same time as
        """

    def prepare():
        """ Prepare the entries for logging. This compacts the entries and checks that
            there's really something to log.
            (Like if something would be added and removed during the same requuest > don't log)
        """

    def format(payload):
        """ Format payload as json.
        """

    def log(payload):
        """ Send payload to the attached logger.
        """

    def commit_hook(status, *args, **kwargs):
        """
        :param status: (bool) Was the transaction successful?
        :param args: Arguments passed from the transaction.
        :param kwargs: Kwargs passed from the transaction.
        """


class ICataloger(IContextAdapter):
    """ Content catalog adapter. """


class IBlobs(IContextAdapter):
    """ Adapter that handles blob storage for a content type.
    """


class IEvolver(IContextAdapter):
    """ Manages upgrades of the database and makes sure the dabase and the
        software version are the same.
    """


class IThumbnails(IContextAdapter):
    thumb_cache = Attribute("Property that returns the IThumbnailsCache utility")

    def get_thumb(scale, key=None, direction="thumbnail"):
        """ Return the arche.models.thumbnails.Thumbnail object.
            If it doesn't exist, it will be created first.

            key will default to the context.blob_key attribute if it's None
        """

    def invalidate_context_cache():
        """ Invalidate the cache relevat to the context that the adapter wrapped.
        """


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


class IRevisions(IContextAdapter, IImmutableDict):
    """ Keeps track of revisions for attributes.
    """
    def __delitem__(key):
        """ Only allows delete of first or last item.
        """


class IReferenceGuards(Interface):
    """ Request adapter to interact with the reference guards.
        Use the request attribute 'reference_guards' to interact with it.
    """
    request = Attribute("Wrapped request instance")
    moving_uids = Attribute("Any UIDs that are marked as currently moving")

    def __init__(request):
        pass

    def get_valid(context):
        """ Return a generator with valid reference guards for this context.
        """

    def check(context):
        """ Check before actually allowing delete.
            Will raise ReferenceGuarded exception if something goes wrong.
        """

    def get_vetoing(context):
        """ Get all reference guards that would veto the removal of this context.
        """

    def moving(uid):
        """ Mark the current UID as moving, so allow it to be removed. """


#/Adapters


#Utils or settings
class IRefGuard(Interface):
    callable = Attribute("Callable that returns referenced objects.")
    name = Attribute("Utility name, must be unique.")
    title = Attribute("Translation string with human-readable title")
    requires = Attribute("Tuple of interfaces required by the guarded context. "
                         "If it's not provided, the context won't be guarded.")
    catalog_result = Attribute("Does the callable return a catalog result "
                               "rather than a list of objects? "
                               "Catalog results are always tuples with a result "
                               "object and a docids IFSet")
    allow_move = Attribute("Bool - does this guard allow objects to be moved? "
                           "(I.e. not URL-dependant) Anything referencing a UID for instance, "
                           "should always be allowed to move.")

    def __init__(_callable,
                 name=None,
                 requires=(IBase,),
                 title=None,
                 catalog_result=False,
                 allow_move=True):
        """ Init with defaults """

    def __call__(request, context):
        """ Check the context. """

    def valid_context(context):
        """ Is this context valid/relevant to this guard? """

    def get_guarded_count(self, request, context):
        """ Return the exact count of objects that would veto.
            Always return the exact count regardless of the users permission.
        """

    def get_guarded_objects(request, context, perm=None, limit=5):
        """ Returns iterator with guarded objects.
            These are ment to be shown to the user who's action was blocked,
            so respecting view permission is a good idea.
        """


class IACLRegistry(Interface):
    pass


class ICatalogIndexes(Interface):
    """ Works as a registry to keep track of all of this or other packages catalog indexes.
    """

    def __call__():
        """ Return a dict where index names are keys and values are the catalog
            index objects that should be stored in the catalog.
        """


class IThumbnailsCache(Interface):
    """ Caches created thumbnails.
        By default this is an instance of repoze.lru.LRUCache

        Value will be arche.models.thumbnails.Thumbnail objects
    """
    def clear():
        """ Empty the cache
        """

    def get(key, default=None):
        """ Get thumbnail
        """

    def put(key, val):
        """ Store thumbnail
        """

    def invalidate(key):
        """ Invalidate a specific key
        """


class IScript(Interface):
    name = Attribute("Name, must be unique.")
    title = Attribute("Human-readable name")
    description = Attribute("Human-readable description")
    callable = Attribute("The script to actually execute. "
                         "It must accept env and parsed_ns as arguments.")
    can_commit = Attribute("Can this script commit to database?")
    argparser = Attribute("A custom argparser instance for this script. See the help-script for an example.")

    def __init__(_callable, **kw):
        """ callable is a must, noticable keywords is argparser
        which stores a custom version of the argparser for this script.
        Always make that argparser inherit the default values, by using:

        argparse.ArgumentParser(parents=[default_parser])
    """

    def __call__(env, script_args):
        """ Scripts are called with the env dict, containing bootstrapped Pyramid instance.
            It's basically what's returned by running pyramid.paster.bootstrap

            The script_args var is a list of command line args that will be parsed.
        """

    def start(env, parsed_ns):
        """ Called right before the script callable is called. """

    def cleanup(env, parsed_ns):
        """ Called after the script has completed or failed. """

#/Utils


class IPortlet(Interface):
    pass


class IPortletType(Interface):
    name = Attribute("Unique name for portlet, works like an ID.")
    schema_factory = Attribute("colander.Schema for this type, or None")
    title = Attribute("Title")
    tpl = Attribute("Template to use")
    portlet = Attribute("IPortlet object to render")
    context = Attribute("""
        The context this portlet was originaly created at.
        (I.e. the place where the PortletFolders will be)
        It doesn't have to be the same context as the current request.
    """)

    def visible(context, request, view, **kwargs):
        """ Check if the portlet should be visible or not.
        """

    def render(context, request, view, **kwargs):
        """ Render portlet
        """


class IPortletManager(IDict):


    def add(slot, portlet_type, **kw):
        pass

    def get_portlets(slot, portlet_type = None):
        pass

    def remove(slot, portlet_uid):
        pass

    def visible(slot, context, request, view, **kw):
        pass

    def render_slot(slot, context, request, view, **kw):
        pass


class IFileUploadTempStore(Interface):
    pass


class IRegistrationTokens(Interface):
    pass


class IEmailValidationTokens(Interface):
    pass
