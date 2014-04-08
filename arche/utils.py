import inspect
from hashlib import sha512

from slugify import slugify
from zope.interface import providedBy
from zope.interface import implementer
from zope.interface.interfaces import ComponentLookupError
from zope.component import adapter
from pyramid.interfaces import IRequest
from pyramid.interfaces import IView
from pyramid.interfaces import IViewClassifier
from pyramid.compat import map_
from pyramid.renderers import render
from pyramid.threadlocal import get_current_request
from pyramid.threadlocal import get_current_registry

from arche.interfaces import IFlashMessages
from arche import _


def add_content_factory(config, ctype):
    assert inspect.isclass(ctype)
    factories = get_content_factories(config.registry)
    type_name = ctype.__name__
    factories[type_name] = ctype

def get_content_factories(registry = None):
    if registry is None:
        registry = get_current_registry()
    return registry.settings['arche.content_factories']

def add_content_schema(config, type_name, schema, name):
    assert inspect.isclass(schema)
    if inspect.isclass(type_name):
        type_name = type_name.__name__
    schemas = get_content_schemas(config.registry)
    ctype_schemas = schemas.setdefault(type_name, {})
    ctype_schemas[name] = schema

def get_content_schemas(registry = None):
    if registry is None:
        registry = get_current_registry()
    return registry.settings['arche.content_schemas']

def add_content_view(config, type_name, name, title = u''):
    if not name:
        raise ValueError("Name must be specified and can't be an empty string. Specify 'view' to override the default view.")
    if inspect.isclass(type_name):
        type_name = type_name.__name__
    content_factories = get_content_factories(config.registry)
    if type_name not in content_factories:
        raise KeyError('No content type with name %s' % type_name)
    views = get_content_views(config.registry)
    ctype_views = views.setdefault(type_name, {})
    ctype_views[name] = title

def get_content_views(registry = None):
    if registry is None:
        registry = get_current_registry()
    return registry.settings['arche.content_views']

def generate_slug(parent, text, limit=40):
    """ Suggest a name for content that will be added.
        text is a title or similar to be used.
    """
    text = unicode(text)
    suggestion = slugify(text[:limit])
    if not len(suggestion):
        raise ValueError("When text was made URL-friendly, nothing remained.")
    request = get_current_request()
    #Is the suggested ID already unique?
    if check_unique_name(parent, request, suggestion):
        return suggestion
    #ID isn't unique, let's try to generate a unique one.
    RETRY = 100
    i = 1
    while i <= RETRY:
        new_s = "%s-%s" % (suggestion, str(i))
        if check_unique_name(parent, request, new_s):
            return new_s
        i += 1
    #If no id was found, don't just continue
    raise KeyError("No unique id could be found")

def check_unique_name(context, request, name):
    """ Check if there's an object with the same name or a registered view with the same name.
        If there is, return False.
    """
    if name in context:
        return False
    provides = [IViewClassifier] + map(providedBy, (request, context))
    if request.registry.adapters.lookup(provides, IView, name=name):
        return False
    return True

def get_view(context, request, view_name = ''):
    """ Returns view callable if a view is registered.
    """
    provides = [IViewClassifier] + map_(
        providedBy,
        (request, context)
    )
    return request.registry.adapters.lookup(provides, IView, name=view_name)

@adapter(IRequest)
@implementer(IFlashMessages)
class FlashMessages(object):
    """ See IFlashMessages"""

    def __init__(self, request):
        self.request = request

    def add(self, msg, type='info', dismissable = True, auto_destruct = True):
        css_classes = ['alert']
        css_classes.append('alert-%s' % type)
        if dismissable:
            css_classes.append('alert-dismissable')
        if auto_destruct:
            css_classes.append('fika-auto-destruct')
        css_classes = " ".join(css_classes)
        flash = {'msg':msg, 'dismissable': dismissable, 'css_classes': css_classes}
        self.request.session.flash(flash)

    def get_messages(self):
        for message in self.request.session.pop_flash():
            yield message

    def render(self):
        response = {'get_messages': self.get_messages}
        return render("arche:templates/flash_messages.pt", response, request = self.request)

def get_flash_messages(request):
    try:
        return request.registry.getAdapter(request, IFlashMessages)
    except ComponentLookupError:
        return FlashMessages(request)

def hash_method(value, registry = None):
    if registry is None:
        registry = get_current_registry()
    return registry.settings['arche.hash_method'](value)

def default_hash_method(value):
    return sha512(value).hexdigest()

def includeme(config):
    config.registry.registerAdapter(FlashMessages)
    config.add_directive('add_content_factory', add_content_factory)
    config.add_directive('add_content_schema', add_content_schema)
    config.add_directive('add_content_view', add_content_view)
