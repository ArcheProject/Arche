from UserDict import IterableUserDict
from collections import deque
from datetime import datetime
import inspect

from BTrees.OOBTree import OOBTree
from html2text import HTML2Text
from pyramid.compat import map_
from pyramid.i18n import TranslationString
from pyramid.interfaces import IView
from pyramid.interfaces import IViewClassifier
from pyramid.threadlocal import get_current_registry
from pyramid.threadlocal import get_current_request
from pyramid.traversal import find_root
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message
from six import string_types
from slugify import UniqueSlugify
from zope.component import adapter
from zope.interface import implementer
from zope.interface import providedBy
from zope.interface.interfaces import ComponentLookupError
import pytz

from arche import _
from arche import logger
from arche.interfaces import (IFlashMessages,
                              IThumbnailedContent,
                              IRoot,
                              IRegistrationTokens,
                              IDateTimeHandler,
                              IContentView)
from arche.models.blob import BlobFile #Keep untill db changed
from arche.models.mimetype_views import get_mimetype_views #b/c


def add_content_factory(config, ctype, addable_to = (), addable_in = ()):
    """ Add a class as a content factory. It will be addable through the add menu
        for anyone with the correct add permission, in a context where it's marked
        as addable. You may set an addable context here as well.
        
        Example:
            config.add_content_factory(MyClass, addable_to = ('Root', 'Document',), addable_in = 'Image')
    """
    assert inspect.isclass(ctype)
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

def add_content_schema(config, type_name, schema, names):
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

def get_content_schemas(registry = None):
    if registry is None:
        registry = get_current_registry()
    return getattr(registry, '_content_schemas', {})

def add_content_view(config, type_name, name, view_cls):
    """ Register a view as selectable for a content type.
        view_cls must implement IContentView.
    """
    assert IContentView.implementedBy(view_cls), "view_cls argument must be a class that implements arche.interfaces.IContentView"
    if not name:
        raise ValueError("Name must be specified and can't be an empty string. Specify 'view' to override the default view.")
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
    scales[name] = (width, height)

def get_image_scales(registry = None):
    if registry is None:
        registry = get_current_registry()
    return getattr(registry, '_image_scales', {})

def thumb_url(request, context, scale, key = 'image'):
    scales = get_image_scales(request.registry)
    if scale in scales:
        if IThumbnailedContent.providedBy(context):
            return request.resource_url(context, 'thumbnail', key, scale)

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

def get_dt_handler(request):
    return IDateTimeHandler(request)

def utcnow():
    """Get the current datetime localized to UTC.
    The difference between this method and datetime.utcnow() is
    that datetime.utcnow() returns the current UTC time but as a naive
    datetime object, whereas this one includes the UTC tz info."""
    return pytz.utc.localize(datetime.utcnow())

def send_email(subject, recipients, html, sender = "noreply@localhost.com", plaintext = None, request = None, send_immediately = False, **kw):
    """ Send an email to users. This also checks the required settings and translates
        the subject.
        
        returns the message object sent, or None
    """
    if request is None:
        request = get_current_request()
    if isinstance(subject, TranslationString):
        subject = request.localizer.translate(subject)
    if isinstance(recipients, string_types):
        recipients = (recipients,)
    if plaintext is None:
        html2text = HTML2Text()
        html2text.ignore_links = True
        html2text.ignore_images = True
        html2text.body_width = 0
        plaintext = html2text.handle(html).strip()
    if not plaintext:
        plaintext = None #In case it was an empty string
    #It seems okay to leave sender blank since it's part of the default configuration
    msg = Message(subject = subject,
                  recipients = recipients,
                  sender = sender,
                  body = plaintext,
                  html = html,
                  **kw)
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


image_mime_to_title = {'image/jpeg': _("JPEG"),
                       'image/png': _("PNG"),
                       'image/gif': _("GIF")}
#FIXME: Add more codecs that work for web!


def _root(request):
    return find_root(request.context)

def includeme(config):
    config.registry.registerAdapter(RegistrationTokens)
    config.add_directive('add_content_factory', add_content_factory)
    config.add_directive('add_addable_content', add_addable_content)
    config.add_directive('add_content_schema', add_content_schema)
    config.add_directive('add_content_view', add_content_view)
    config.add_directive('add_image_scale', add_image_scale)
    config.add_request_method(thumb_url, name = 'thumb_url')
    config.add_request_method(get_dt_handler, name = 'dt_handler', reify = True)
    config.add_request_method(_root, name = 'root', reify = True)
    
    #Init default scales
    for (name, scale) in image_scales.items():
        config.add_image_scale(name, *scale)
