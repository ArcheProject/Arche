import inspect
from hashlib import sha512
from StringIO import StringIO
from UserDict import IterableUserDict

from slugify import slugify
from persistent import Persistent
from zope.interface import providedBy
from zope.interface import implementer
from zope.interface.interfaces import ComponentLookupError
from zope.component import adapter
from BTrees.OOBTree import OOBTree
from ZODB.blob import Blob
from plone.scale.scale import scaleImage
from pyramid.interfaces import IRequest
from pyramid.interfaces import IView
from pyramid.interfaces import IViewClassifier
from pyramid.compat import map_
from pyramid.renderers import render
from pyramid.threadlocal import get_current_request
from pyramid.threadlocal import get_current_registry

from arche.interfaces import * #FIXME: Pick import
from arche import _


def add_content_factory(config, ctype):
    assert inspect.isclass(ctype)
    factories = get_content_factories(config.registry)
    factories[ctype.type_name] = ctype

def get_content_factories(registry = None):
    if registry is None:
        registry = get_current_registry()
    return registry._content_factories

def add_addable_content(config, ctype, addable_to):
    addable = config.registry._addable_content.setdefault(ctype, set())
    if isinstance(addable_to, basestring):
        addable.add(addable_to)
    else:
        addable.update(addable_to)

def get_addable_content(registry = None):
    if registry is None:
        registry = get_current_registry()
    return registry._addable_content

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
    return registry._content_schemas

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
    views = get_content_views(config.registry)
    ctype_views = views.setdefault(type_name, {})
    ctype_views[name] = view_cls

def get_content_views(registry = None):
    if registry is None:
        registry = get_current_registry()
    return registry._content_views

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
            css_classes.append('auto-destruct')
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

def upload_stream(stream, _file):
    size = 0
    while 1:
        data = stream.read(1<<21)
        if not data:
            break
        size += len(data)
        _file.write(data)
    return size


class FileUploadTempStore(object):
    """
    A temporary storage for file file uploads

    File uploads are stored in the session so that you don't need
    to upload your file again if validation of another schema node
    fails.
    """

    def __init__(self, request):
        self.session = request.session

    def keys(self):
        return [k for k in self.session.keys() if not k.startswith('_')]

    def get(self, key, default = None):
        return key in self.keys() and self.session[key] or default

    def __setitem__(self, name, value):
        value = value.copy()
        fp = value.pop('fp')
        value['file_contents'] = fp.read()
        fp.seek(0)
        self.session[name] = value

    def __getitem__(self, name):
        value = self.session[name].copy()
        value['fp'] = StringIO(value.pop('file_contents'))
        return value

    def __delitem__(self, name):
        del self.session[name]

    def preview_url(self, name):
        return None


@implementer(IBlobs)
@adapter(IBase)
class Blobs(IterableUserDict):
    """ Adapter that handles blobs in context
    """
    def __init__(self, context):
        self.context = context
        self.data = getattr(context, '__blobs__', {})

    def __setitem__(self, key, item):
        if not isinstance(item, BlobFile):
            raise ValueError("Only instances of BlobFile allowed.")
        if not isinstance(self.data, OOBTree):
            self.data = self.context.__blobs__ = OOBTree()
        self.data[key] = item

    def create(self, key, overwrite = False):
        if key not in self or (key in self and overwrite):
            self[key] = BlobFile()
        return self[key]

    def create_from_formdata(self, key, value):
        """ Handle creation of a blob from a deform.FileUpload widget.
            Expects the following keys in value.
            
            fp
                A file stream
            filename
                Filename
            mimetype
                Mimetype
            
        """
        if value:
            bf = self.create(key)
            with bf.blob.open('w') as f:
                bf.filename = value['filename']
                bf.mimetype = value['mimetype']
                fp = value['fp']
                bf.size = upload_stream(fp, f)
        else:
            if key in self:
                del self[key]


class BlobFile(Persistent):
    size = None
    mimetype = ""
    filename = ""
    blob = None

    def __init__(self, size = None, mimetype = "", filename = ""):
        super(BlobFile, self).__init__()
        self.size = size
        self.mimetype = mimetype
        self.filename = filename
        self.blob = Blob()


@implementer(IThumbnails)
@adapter(IThumbnailedContent)
class Thumbnails(object):
    """ Get a thumbnail image. A good place to add caching and similar in the future. """

    def __init__(self, context):
        self.context = context

    def get_thumb(self, scale, key = "image", direction = "thumb"):
        """ Return data from plone scale or None"""
        scales = get_image_scales()
        maxwidth, maxheight = scales[scale]
        blobs = IBlobs(self.context)
        if key in blobs:
            with blobs[key].blob.open() as f:
                thumb_data, image_type, size = scaleImage(f, width = maxwidth, height = maxheight, direction = direction)
            return Thumbnail(thumb_data, image_type = image_type, size = size)


class Thumbnail(object):
    width = 0
    height = 0
    image_type = u""
    image = None

    def __init__(self, image, size = None, image_type = u""):
        self.width, self.height = size
        self.image = image
        self.image_type = image_type

    @property
    def mimetype(self):
        return "image/%s" % self.image_type


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


def get_image_scales(registry = None):
    if registry is None:
        registry = get_current_registry()
    return registry._image_scales

def thumb_url(request, context, scale, key = 'image'):
    scales = get_image_scales(request.registry)
    if scale in scales:
        if IThumbnailedContent.providedBy(context) and IBlobs(context).get(key, None) is not None:
            return request.resource_url(context, 'thumbnail', key, scale)

def find_all_db_objects(context):
    """ Return all objects stored in context.values(), and all subobjects.
        Great for reindexing the catalog or other database migrations.
    """
    #FIXME: This should be a generator instead. With a large database, it will require a lot of memory and time otherwise
    result = set()
    result.add(context)
    if hasattr(context, 'values'):
        for obj in context.values():
            result.update(find_all_db_objects(obj))
    return result


def includeme(config):
    config.registry.registerAdapter(FlashMessages)
    config.registry.registerAdapter(Thumbnails)
    config.registry.registerAdapter(Blobs)
    config.registry._content_factories = {}
    config.registry._content_schemas = {}
    config.registry._content_views = {}
    config.registry._image_scales = image_scales
    config.registry._addable_content = {}
    config.add_directive('add_content_factory', add_content_factory)
    config.add_directive('add_addable_content', add_addable_content)
    config.add_directive('add_content_schema', add_content_schema)
    config.add_directive('add_content_view', add_content_view)
