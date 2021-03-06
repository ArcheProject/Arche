from uuid import uuid4

from zope.component import adapter
from zope.interface import implementer
from plone.scale.scale import scaleImage
from repoze.lru import LRUCache
from pyramid.threadlocal import get_current_registry
from PIL.Image import core as pilcore

from arche.interfaces import IBlobs, IThumbnailsCache
from arche.interfaces import IThumbnailedContent
from arche.interfaces import IThumbnails
from arche.interfaces import IObjectUpdatedEvent
from arche.utils import get_image_scales


@implementer(IThumbnails)
@adapter(IThumbnailedContent)
class Thumbnails(object):
    """ Get a thumbnail image. A good place to add caching and similar in the future. """

    def __init__(self, context):
        self.context = context

    def get_thumb(self, scale, key = None, direction = "thumbnail"):
        """ Return data from plone scale or None"""
        #Make cache optional
        if key is None:
            key = getattr(self.context, 'blob_key', 'image')
        cachekey = (self.context.uid, scale, key, direction)
        cached = self.thumb_cache.get(cachekey)
        if cached:
            return cached
        if direction not in _ALLOWED_SCALE_DIRECTIONS:
            return
        scales = get_image_scales()
        maxwidth, maxheight = scales[scale]
        blobs = IBlobs(self.context)
        if key in blobs:
            registry = get_current_registry()
            if blobs[key].mimetype in registry.settings['supported_thumbnail_mimetypes']:
                with blobs[key].blob.open() as f:
                    try:
                        thumb_data, image_type, size = scaleImage(
                            f, width = maxwidth, height = maxheight, direction = direction
                        )
                    except IOError:
                        #FIXME: Logging?
                        return
                thumb = Thumbnail(thumb_data, image_type = image_type, size = size)
                self.thumb_cache.put(cachekey, thumb)
                return thumb

    def invalidate_context_cache(self):
        invalidate_keys = set()
        for k in self.thumb_cache.data.keys():
            if self.context.uid in k:
                invalidate_keys.add(k)
        for k in invalidate_keys:
            self.thumb_cache.invalidate(k)

    @property
    def thumb_cache(self):
        reg = get_current_registry()
        return reg.queryUtility(IThumbnailsCache)


class Thumbnail(object):
    """ Note that these are non-persistent objects usually created on the fly."""
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


def invalidate_thumbs_in_context(context, event):
    IThumbnails(context).invalidate_context_cache()


_pil_codecs_to_mimetypes = {
    'jpeg_encoder': ('image/jpeg', 'image/pjpeg',),
    'zip_encoder': ('image/png',),
    'gif_encoder': ('image/gif',),
}
_ALLOWED_SCALE_DIRECTIONS = (
    'thumbnail',
    'down',
    'up'
)


def _check_supported_thumbnail_mimetypes():
    results = set()
    pil_methods = dir(pilcore)
    for (k, v) in _pil_codecs_to_mimetypes.items():
        if k in pil_methods:
            results.update(v)
    return results


def thumb_url(request, context, scale, key = None, direction = 'thumbnail'):
    if key is None:
        key = getattr(context, 'blob_key', 'image')
    scales = get_image_scales(request.registry)
    if scale in scales and IThumbnailedContent.providedBy(context) and key in IBlobs(context, ()):
        return request.resource_url(context, 'thumbnail', key, scale, direction)


def thumb_tag(request, context, scale_name, default = u"", extra_cls = '', direction = "thumbnail", key = None, **kw):
    #FIXME: Default?
    if key is None:
        key = getattr(context, 'blob_key', 'image')
    url = request.thumb_url(context, scale_name, key = key, direction = direction)
    if not url:
        return default
    thumbnails = request.registry.queryAdapter(context, IThumbnails)
    if thumbnails is None:
        return default
    thumb = thumbnails.get_thumb(scale_name, direction = direction, key = key)
    if thumb:
        data = {'src': url,
                'width': thumb.width,
                'height': thumb.height,
                'class': 'thumb-%s img-responsive' % scale_name,
                'alt': context.title,
                }
        if extra_cls:
            data['class'] += " %s" % extra_cls
        data.update(kw)
        return u"<img %s />" % " ".join(['%s="%s"' % (k, v) for (k, v) in data.items()])
    return default


@implementer(IThumbnailsCache)
class ThumbCache(LRUCache):
    __doc__ = LRUCache.__doc__


def includeme(config):
    config.add_subscriber(invalidate_thumbs_in_context, [IThumbnailedContent, IObjectUpdatedEvent])
    config.registry.registerAdapter(Thumbnails)
    config.registry.settings['supported_thumbnail_mimetypes'] = _check_supported_thumbnail_mimetypes()
    config.add_request_method(thumb_url, name = 'thumb_url')
    config.add_request_method(thumb_tag, name = 'thumb_tag')
    thumb_cache = ThumbCache(100)
    config.registry.registerUtility(thumb_cache)
