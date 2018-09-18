import inspect
import warnings
from collections import deque
from datetime import datetime
from uuid import uuid4

import pytz
from BTrees.OOBTree import OOBTree
from html2text import HTML2Text
from persistent import IPersistent
from pyramid.compat import map_
from pyramid.httpexceptions import HTTPUnauthorized
from pyramid.i18n import TranslationString
from pyramid.interfaces import IView
from pyramid.interfaces import IViewClassifier
from pyramid.location import inside
from pyramid.threadlocal import get_current_registry
from pyramid.threadlocal import get_current_request
from pyramid.traversal import find_resource
from pyramid.traversal import find_root
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message
from six import string_types
from slugify import UniqueSlugify
from zope.component import adapter
from zope.component.event import objectEventNotify
from zope.copy import copy
from zope.copy.interfaces import ICopyHook
from zope.copy.interfaces import ResumeCopy
from zope.interface import implementer
from zope.interface import providedBy
from zope.interface.interfaces import ComponentLookupError

from arche import _
from arche import logger
from arche.compat import IterableUserDict
from arche.interfaces import IContentView
from arche.interfaces import IDateTimeHandler
from arche.interfaces import IEmailValidationTokens
from arche.interfaces import IFlashMessages
from arche.interfaces import IRegistrationTokens
from arche.interfaces import IRoot
from arche.interfaces import IUser
from arche.models.blob import BlobFile #Keep untill db changed
from arche.models.mimetype_views import get_mimetype_views #b/c
from arche.security import PERM_VIEW


def add_content_factory(config, ctype, addable_to = (), addable_in = ()):
    """ Add a class as a content factory/resource.
        It will be addable through the add menu
        for anyone with the correct add permission, in a context where it's marked
        as addable.

        Example:
            config.add_content_factory(MyClass, addable_to = ('Root', 'Document',), addable_in = 'Image')
    """
    assert inspect.isclass(ctype)
    if not getattr(ctype, 'type_name', None):
        name = ctype.__name__
        logger.debug("%r got type_name %r", ctype, name)
        ctype.type_name = name
    if not hasattr(ctype, 'add_permission'):
        add_perm = "Add %s" % ctype.type_name
        logger.debug("%r got add_permission %r.", ctype, add_perm)
        ctype.add_permission = add_perm
    try:
        factories = config.registry._content_factories
    except AttributeError:
        factories = config.registry._content_factories = {}
    factories[ctype.type_name] = ctype
    if addable_to:
        config.add_addable_content(ctype.type_name, addable_to)
    if addable_in:
        if isinstance(addable_in, string_types):
            addable_in = (addable_in,)
        for ctype_name in addable_in:
            config.add_addable_content(ctype_name, ctype.type_name)


def get_content_factories(registry = None):
    if registry is None:
        registry = get_current_registry()
    return getattr(registry, '_content_factories', {})


def content_factories(request):
    return get_content_factories(request.registry)


def add_addable_content(config, ctype, addable_to):
    try:
        addable_content = config.registry._addable_content
    except AttributeError:
        addable_content = config.registry._addable_content = {}
    addable = addable_content.setdefault(ctype, set())
    if isinstance(addable_to, string_types):
        addable.add(addable_to)
    else:
        addable.update(addable_to)


def get_addable_content(registry = None):
    if registry is None:
        registry = get_current_registry()
    return getattr(registry, '_addable_content', {})


def add_schema(config, type_name, schema, names):
    assert inspect.isclass(schema)
    if inspect.isclass(type_name):
        type_name = type_name.__name__
    try:
        schemas = config.registry._content_schemas
    except AttributeError:
        schemas = config.registry._content_schemas = {}
    ctype_schemas = schemas.setdefault(type_name, {})
    if isinstance(names, string_types):
        names = (names,)
    for name in names:
        ctype_schemas[name] = schema


def add_content_schema(config, type_name, schema, names):
    #Backwards compat
    warnings.warn(
        'add_content_schema is deprecated, use add_schema instead',
        DeprecationWarning,
    )
    config.add_schema(type_name, schema, names)


def get_content_schemas(registry = None):
    if registry is None:
        registry = get_current_registry()
    return getattr(registry, '_content_schemas', {})


def add_content_view(config, type_name, name, view_cls):
    """ Register a view as selectable for a content type.
        view_cls must implement IContentView.
    """
    assert IContentView.implementedBy(view_cls), "view_cls argument must be a " \
                                                 "class that implements " \
                                                 "arche.interfaces.IContentView"
    if not name:
        raise ValueError("Name must be specified and can't be an "
                         "empty string. Specify 'view' to override the "
                         "default view.")
    if inspect.isclass(type_name):
        type_name = type_name.type_name
    content_factories = get_content_factories(config.registry)
    if type_name not in content_factories:
        raise KeyError('No content type with name %s' % type_name)
    try:
        views = config.registry._content_views
    except AttributeError:
        views = config.registry._content_views = {}
    ctype_views = views.setdefault(type_name, {})
    ctype_views[name] = view_cls


def get_content_views(registry = None):
    if registry is None:
        registry = get_current_registry()
    return getattr(registry, '_content_views', {})


def generate_slug(parent, text, limit=40):
    """ Suggest a name for content that will be added.
        text is a title or similar to be used.
    """
    #Stop words configurable?
    #We don't have any language settings anywhere
    #Note about kw uids: It's keys already used.
    if not isinstance(text, string_types):
        text = str(text)
    used_names = set(parent.keys())
    request = get_current_request()
    used_names.update(get_context_view_names(parent, request))
    sluggo = UniqueSlugify(to_lower = True,
                           stop_words = ['a', 'an', 'the'],
                           max_length = 80,
                           uids = used_names)
    suggestion = sluggo(text)
    if not len(suggestion):
        raise ValueError("When text was made URL-friendly, nothing remained.")
    if check_unique_name(parent, request, suggestion):
        return suggestion
    raise KeyError("No unique id could be found")


def get_context_view_names(context, request):
    provides = [IViewClassifier] + map_(
        providedBy,
        (request, context)
    )
    return [x for (x, y) in request.registry.adapters.lookupAll(provides, IView)]


def check_unique_name(context, request, name):
    """ Check if there's an object with the same name or a registered view with the same name.
        If there is, return False.
    """
    if name in context:
        return False
    if get_view(context, request, view_name = name) is None:
        return True
    return False


def get_view(context, request, view_name = ''):
    """ Returns view callable if a view is registered.
    """
    provides = [IViewClassifier] + map_(
        providedBy,
        (request, context)
    )
    return request.registry.adapters.lookup(provides, IView, name=view_name)


def get_flash_messages(request):
    try:
        return request.registry.getAdapter(request, IFlashMessages)
    except ComponentLookupError:
        from arche.models.flash_messages import FlashMessages
        return FlashMessages(request)


def hash_method(value, registry = None, hashed = None):
    if registry is None:
        registry = get_current_registry()
    try:
        hasher = registry.settings['arche.hash_method']
    except KeyError:
        logger.warn("No hash method found, importing default. Set arche.hash_method in your paster.ini config.")
        from arche.security import sha512_hash_method
        hasher = sha512_hash_method
    return hasher(value, hashed = hashed)


#Default image scales - mapped to twitter bootstrap columns
image_scales = {
    'icon': [20, 20],
    'mini': [40, 40],
    'square': [64, 64],
    'col-1': [60, 120],
    'col-2': [160, 320],
    'col-3': [260, 520],
    'col-4': [360, 720],
    'col-5': [460, 920],
    'col-6': [560, 1120],
    'col-7': [660, 1320],
    'col-8': [760, 1520],
    'col-9': [860, 1720],
    'col-10': [960, 1920],
    'col-11': [1060, 2120],
    'col-12': [1160, 2320],
    }


def add_image_scale(config, name, width, height):
    try:
        scales = config.registry._image_scales
    except AttributeError:
        scales = config.registry._image_scales = {}
    for v in [width, height]:
        assert isinstance(v, int), "Height and with of image scales must be integers"
    scales[name] = (width, height)


def get_image_scales(registry = None):
    if registry is None:
        registry = get_current_registry()
    return getattr(registry, '_image_scales', {})


def find_all_db_objects(root):
    """ Return all objects stored in context.values(), and all subobjects.
        Great for reindexing the catalog or other database migrations.
    """
    stack = deque([root])
    while stack:
        obj = stack.popleft()
        try:
            stack.extend(obj for obj in obj.values())
        except AttributeError:
            pass
        yield obj


def move_resources(request, to_move, new_parent, name=None):
    """ Move one resource an everything contained in it to another location (or name)"""
    old_parent = to_move.__parent__
    if old_parent is None:
        raise TypeError("The object you're trying to move doesn't have a parent.")
    if name is None:
        name = to_move.__name__
    name = generate_slug(new_parent, name)
    #Notify reference guards of attempted move
    for obj in find_all_db_objects(to_move):
        request.reference_guards.moving(obj.uid)
    del old_parent[to_move.__name__]
    new_parent[name] = to_move


def copy_recursive(original_contex, change_uids = True):
    """ Note that a copy should always have changed UIDs if the original is kept
        in the resource tree.
    """
    new_context = copy(original_contex)
    for obj in find_all_db_objects(new_context):
        if change_uids and hasattr(obj, 'uid'):
            obj.uid = unicode(uuid4())
    return new_context


def get_dt_handler(request):
    return IDateTimeHandler(request)


def utcnow():
    """Get the current datetime localized to UTC.
    The difference between this method and datetime.utcnow() is
    that datetime.utcnow() returns the current UTC time but as a naive
    datetime object, whereas this one includes the UTC tz info."""
    return pytz.utc.localize(datetime.utcnow())


def compose_email(request, subject, recipients, html, sender = None, plaintext = None, **kw):
    """
    :param request:
    :param subject: Email subject
    :param recipients: A list of recipients
    :param html: HTML-version of the email
    :param sender: Should normally be None so it's fetched from the default configuration.
    :param plaintext: A custom plaintext version. By default, it will be created from the HTML-version
    :param **kw: Extra keywords to send to the message constructor
    :return: A Pyramid mailer Message object
    """
    if isinstance(subject, TranslationString):
        subject = request.localizer.translate(subject)
    if isinstance(recipients, string_types):
        recipients = (recipients,)
    if plaintext is None:
        html2text = HTML2Text()
        html2text.ignore_links = False
        html2text.ignore_images = True
        html2text.body_width = 0
        plaintext = html2text.handle(html).strip()
    if not plaintext:
        plaintext = None #In case it was an empty string
    #It seems okay to leave sender blank since it's part of the default configuration
    return Message(
        subject = subject,
        recipients = recipients,
        sender = sender,
        body = plaintext,
        html = html,
        **kw
    )


def send_email(request, subject, recipients, html, sender = None, plaintext = None, send_immediately = False, **kw):
    """ Send an email to users. This also checks the required settings and translates
        the subject.

        returns the message object sent, or None
    """
    msg = compose_email(request, subject, recipients, html, sender = None, plaintext = None, **kw)
    mailer = get_mailer(request)
    #Note that messages are sent during the transaction process. See pyramid_mailer docs
    if send_immediately:
        mailer.send_immediately(msg)
    else:
        mailer.send(msg)
    return msg


class AttributeAnnotations(IterableUserDict):
    """ Handles a named storage for keys/values. It's always a named adapter
        and the name attribute should be the same as the name it was registered with.
    """
    attr_name = None

    def __init__(self, context):
        self.context = context
        try:
            self.data = getattr(context, self.attr_name)
        except AttributeError:
            setattr(context, self.attr_name, OOBTree())
            self.data = getattr(context, self.attr_name)

    def __repr__(self):
        klass = self.__class__
        classname = '%s.%s' % (klass.__module__, klass.__name__)
        return '<%s object at %#x>' % (classname, id(self),)


@implementer(IRegistrationTokens)
@adapter(IRoot)
class RegistrationTokens(AttributeAnnotations):
    attr_name = '__registration_tokens__'

    def cleanup(self):
        expired = set()
        for (email, token) in self.items():
            if not token.valid:
                expired.add(email)
        for email in expired:
            del self[email]


@implementer(IEmailValidationTokens)
@adapter(IUser)
class EmailValidationTokens(AttributeAnnotations):
    attr_name = '__email_validation_tokens__'

    def new(self, email):
        factory = get_content_factories()['Token']
        self[email] = factory(size = 15)
        return self[email]

    def cleanup(self):
        expired = set()
        for (email, token) in self.items():
            if not token.valid:
                expired.add(email)
        for email in expired:
            del self[email]


#FIXME: Add more codecs that work for web!
#FIXME: This should be a proper util instead
image_mime_to_title = {'image/jpeg': "JPEG",
                       'image/png': "PNG",
                       'image/gif': "GIF"}


def get_root(request):
    return find_root(getattr(request, 'context', None))


def get_profile(request):
    if request.authenticated_userid:
        return request.root.get('users', {}).get(request.authenticated_userid, None)


def resolve_docids(request, docids, perm = PERM_VIEW):
    if isinstance(docids, int):
        docids = (docids,)
    for docid in docids:
        path = request.root.document_map.address_for_docid(docid)
        obj = find_resource(request.root, path)
        #FIXME: Have perm check here?
        if perm and not request.has_permission(perm, obj):
            continue
        yield obj


def resolve_uid(request, uid, perm = PERM_VIEW):
    docids = request.root.catalog.query("uid == '%s'" % uid)[1]
    for obj in resolve_docids(request, docids, perm = perm):
        return obj


class _FailMarker(object):
    def __contains__(self, other):
        return False
    def __eq__(self, other):
        return False
    __hash__ = None


fail_marker = _FailMarker()


def prep_html_for_search_indexing(html):
    html2text = HTML2Text()
    html2text.ignore_links = True
    html2text.ignore_images = True
    html2text.body_width = 0
    html2text.unicode_snob = 1
    html2text.ignore_emphasis = 1
    return html2text.handle(html).strip()


def replace_fanstatic_resource(config, to_remove, to_inject):
    """ Use this to remove 'to_remove' from fanstatic, and replace
        all it's dependencies with 'to_inject'.

        Example usage: Use a custom built twitter bootstrap css-file instead.
        
        from fanstatic import Resource
        from js.bootstrap import bootstrap_css #The default one
        
        my_custom = Resource(mylib, 'custom_bootstrap.css')
        
        def includeme(config):
            config.replace_fanstatic_resource(bootstrap_css, my_custom)
    """
    from fanstatic import get_library_registry
    from fanstatic import Resource
    for item in (to_remove, to_inject):
        assert isinstance(item, Resource), "Must be a fanstatic.Resource instance"
    for lib in get_library_registry().values():
        for resource in lib.known_resources.values():
            if to_remove in resource.depends:
                resource.depends.remove(to_remove)
                resource.depends.add(to_inject)
            if to_remove != resource and to_remove in resource.resources:
                resource.resources.remove(to_remove)
                resource.resources.add(to_inject)


def validate_appstruct(request, schema, appstruct, **kw):
    """
    Args:
        schema: colander.Schema
        appstruct: dict
        **kw: bind keywords

    Returns:
        Validated appstruct with defaults + any missing values
    """
    if isinstance(schema, type):
        schema = schema()
    if schema.bindings is None:
        if 'request' not in kw:
            kw['request'] = request
        schema = schema.bind(**kw)
    return schema.deserialize(schema.serialize(appstruct))


def get_schema(request, context, type_name, schema_name, bind = None, event = True):
    schema = get_content_schemas(request.registry)[type_name][schema_name]()
    if event:
        from arche.events import SchemaCreatedEvent
        event = SchemaCreatedEvent(schema, context = context, request = request)
        objectEventNotify(event)
    if bind is None:
        schema = schema.bind(context = context, request = request)
    else:
        schema = schema.bind(**bind)
    return schema


def addable_content(request, context, restrict=True, check_perm=True):
    """ Return a generator with content factories addable in this context.
        If restrict is True, also check custom limitations within this context.
    """
    _marker = object()
    context_type = getattr(context, 'type_name', None)
    if not context_type:
        raise StopIteration()
    factories = request.content_factories
    for (name, addable) in get_addable_content(request.registry).items():
        if context_type not in addable:
            continue
        if restrict and getattr(context, 'custom_addable', None) and name not in context.custom_addable_types:
            continue
        factory = factories.get(name, None)
        if factory is not None:
            add_perm = getattr(factory, 'add_permission', _marker)
            if check_perm and not request.has_permission(add_perm, context):
                continue
            yield factory


def is_modal(request):
    return bool(request.params.get('modal', None) == '1')


def format_traceback():
    import sys
    import traceback
    exception_list = traceback.format_stack()
    exception_list = exception_list[:-2]
    exception_list.extend(traceback.format_tb(sys.exc_info()[2]))
    exception_list.extend(traceback.format_exception_only(sys.exc_info()[0], sys.exc_info()[1]))
    exception_str = "Traceback (most recent call last):\n"
    exception_str += "".join(exception_list)
    return exception_str


class CopyHook(object):
    """ Taken from Substance D - thanks :)"""
    def __init__(self, context):
        self.context = context

    def __call__(self, toplevel, register):
        context = self.context
        # We can't register for a more specific interface than IPersistent so
        # we have to check for __parent__ here (signifiying that the object is
        # located) and do something special rather than just registering a copy
        # hook for things that are guaranteed to have a __parent__ (such as
        # Zope's ILocation)
        if hasattr(context, '__parent__'):
            if not inside(self.context, toplevel):
                # Return the object if we *don't* want it copied.  I don't
                # really quite understand why we return it instead of returning
                # None, and why we raise an exception if we *do* want it copied
                # but mine is not to wonder why.
                return context
        # Otherwise, it's a persistent object that does live inside the object
        # we're copying or a nonpersistent object.  In such cases, we
        # definitely want to copy them and we signify this desire by raising
        # ResumeCopy.
        raise ResumeCopy


def authdebug_message(request):
    """ This method is read by the Pyramid viewderivers to produce an error
        message when a view isn't allowed to be accessed.

        We'll add a small hack here to raise HTTP 401s when unauthenticated.
        It makes a lot more sense.
    """
    if request.authenticated_userid:
        return request.localizer.translate(_("You're not allowed to access this"))
    raise HTTPUnauthorized(request.localizer.translate(_("You might need to login to access this")))


def includeme(config):
    config.registry.registerAdapter(RegistrationTokens)
    config.registry.registerAdapter(EmailValidationTokens)
    config.add_directive('add_content_factory', add_content_factory)
    config.add_directive('add_addable_content', add_addable_content)
    config.add_directive('add_schema', add_schema)
    config.add_directive('add_content_schema', add_content_schema) #b/c
    config.add_directive('add_content_view', add_content_view)
    config.add_directive('add_image_scale', add_image_scale)
    config.add_directive('replace_fanstatic_resource', replace_fanstatic_resource)
    config.add_request_method(get_dt_handler, name = 'dt_handler', reify = True)
    config.add_request_method(get_root, name = 'root', reify = True)
    config.add_request_method(get_profile, name = 'profile', reify = True)
    config.add_request_method(compose_email)
    config.add_request_method(send_email)
    config.add_request_method(resolve_docids)
    config.add_request_method(resolve_uid)
    config.add_request_method(content_factories, property = True)
    config.add_request_method(validate_appstruct)
    config.add_request_method(get_schema)
    config.add_request_method(addable_content)
    config.add_request_method(is_modal, reify=True)
    config.add_request_method(authdebug_message, reify=True)
    #Init default scales
    for (name, scale) in image_scales.items():
        config.add_image_scale(name, *scale)
    # The ICopyHook adapter avoids dumping referenced objects that are not
    # located inside an object containment-wise when that object is copied.  If
    # it is not registered, every copy winds up dumping all the objects in the
    # database due to __parent__ pointers.
    config.registry.registerAdapter(CopyHook, (IPersistent,), ICopyHook)
