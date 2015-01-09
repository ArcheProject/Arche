from UserDict import IterableUserDict

from BTrees.OOBTree import OOBTree
from ZODB.blob import Blob
from deform.widget import filedict
from persistent import Persistent
from zope.component import adapter
from zope.interface import implementer

from arche.interfaces import IBase
from arche.interfaces import IBlobs


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

    def formdata_dict(self, key):
        blob = self.get(key)
        if blob:
            return filedict(mimetype = blob.mimetype,
                            size = blob.size,
                            filename = blob.filename,
                            uid = None) #uid has to be there to make colander happy
            
    def create_from_formdata(self, key, value):
        """ Handle creation of a blob from a deform.FileUpload widget.
            Expects the following keys in value.
            
            fp
                A file stream
            filename
                Filename
            mimetype
                Mimetype
            
            if 'delete' is a present key and set to something that is true,
            data will be deleted.
            
        """
        if value:
            if value.get('delete'):
                if key in self:
                    del self[key]
            else:
                bf = self.create(key)
                with bf.blob.open('w') as f:
                    bf.filename = value['filename']
                    bf.mimetype = value['mimetype']
                    fp = value['fp']
                    bf.size = upload_stream(fp, f)
                return bf


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


def upload_stream(stream, _file):
    size = 0
    while 1:
        data = stream.read(1<<21)
        if not data:
            break
        size += len(data)
        _file.write(data)
    return size


def includeme(config):
    config.registry.registerAdapter(Blobs)
