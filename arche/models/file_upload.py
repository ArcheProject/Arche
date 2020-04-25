# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyramid.interfaces import IRequest
from zope.component import adapter
from zope.interface import implementer
import six

from arche.interfaces import IFileUploadTempStore


@adapter(IRequest)
@implementer(IFileUploadTempStore)
class FileUploadTempStore(object):
    """
    A temporary storage for file uploads

    File uploads are stored in the session so that you don't need
    to upload your file again if validation of another schema node
    fails.
    """

    def __init__(self, request):
        self.request = request

    @property
    def storage(self):
        return self.request.session.setdefault('upload_tmp', {})

    def keys(self):
        return [k for k in self.storage.keys() if not k.startswith('_')]

    def get(self, key, default = None):
        return key in self.keys() and self.storage[key] or default

    def clear(self):
        self.request.session.pop('upload_tmp', None)

    def __setitem__(self, name, value):
        value = value.copy()
        fp = value.pop('fp')
        value['file_contents'] = fp.read()
        fp.seek(0)
        self.storage[name] = value

    def __getitem__(self, name):
        value = self.storage[name].copy()
        value['fp'] = six.BytesIO(value.get('file_contents'))
        return value

    def __delitem__(self, name):
        del self.storage[name]

    def __contains__(self, name):
        return name in self.storage

    def preview_url(self, name):
        #To make deform happy
        return None

def includeme(config):
    config.registry.registerAdapter(FileUploadTempStore, provided=IFileUploadTempStore)
