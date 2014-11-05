from zope.component.event import objectEventNotify
from repoze.folder.events import ObjectAddedEvent
from repoze.folder.events import ObjectWillBeRemovedEvent
from pyramid.threadlocal import get_current_request

from arche.interfaces import IBase
from arche.interfaces import IFolder
from arche.interfaces import IObjectAddedEvent
from arche.interfaces import IObjectUpdatedEvent
from arche.interfaces import IObjectWillBeRemovedEvent
from arche.interfaces import IFileUploadTempStore


def propagate_added_subscriber(context, event):
    for obj in context.values():
        objectEventNotify(ObjectAddedEvent(obj, context, obj.__name__))

def propagate_will_be_removed_subscriber(context, event):
    for obj in context.values():
        objectEventNotify(ObjectWillBeRemovedEvent(obj, context, obj.__name__))

def clear_upload_storage(*args):
    request = get_current_request()
    tmp_storage = IFileUploadTempStore(request, None)
    if tmp_storage:
        tmp_storage.clear()


def includeme(config):
    config.add_subscriber(propagate_added_subscriber, [IFolder, IObjectAddedEvent])
    config.add_subscriber(propagate_will_be_removed_subscriber, [IFolder, IObjectWillBeRemovedEvent])
    config.add_subscriber(clear_upload_storage, [IBase, IObjectAddedEvent])
    config.add_subscriber(clear_upload_storage, [IBase, IObjectUpdatedEvent])
