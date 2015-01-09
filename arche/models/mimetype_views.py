from UserDict import IterableUserDict

import six
from pyramid.threadlocal import get_current_registry


class MIMETypeViews(IterableUserDict):

    def __getitem__(self, key):
        try:
            return self.data[key]
        except KeyError:
            pass
        try:
            main_key = key.split('/')[0]
            return self.data["%s/*" % main_key]
        except KeyError:
            raise KeyError("Mime type %s wasn't found in views")

    def get(self, key, failobj=None):
        if key not in self:
            key = "%s/*" % key.split('/')[0]
            if key not in self:
                return failobj
        return self[key]

    def __contains__(self, key):
        return key in self.data or "%s/*" % key.split('/')[0] in self.data


def add_mimetype_view(config, mimetype, view_name):
    """ Add a view for a specific mimetype.
        Mimetypes can be specified with a wildcard as second part, like movie/*
        view_name must be a registered view.
    """
    assert isinstance(mimetype, six.string_types), "%s is not a string" % mimetype
    assert isinstance(view_name, six.string_types), "%s is not a string" % view_name
    views = get_mimetype_views(config.registry)
    if not isinstance(views, MIMETypeViews):
        config.registry._mime_type_views = views = MIMETypeViews()
    views[mimetype] = view_name

def get_mimetype_views(registry = None):
    """ Returns a MIMETypeViews object or a dict.
    """
    if registry is None:
        registry = get_current_registry()
    return getattr(registry, '_mime_type_views', {})

def includeme(config):
    config.add_directive('add_mimetype_view', add_mimetype_view)
