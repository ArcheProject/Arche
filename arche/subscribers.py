from pyramid.threadlocal import get_current_registry
from pyramid.threadlocal import get_current_request
from repoze.folder.events import ObjectAddedEvent
from repoze.folder.events import ObjectWillBeRemovedEvent
from zope.component.event import objectEventNotify

from arche.interfaces import IBase
from arche.interfaces import IFolder
from arche.interfaces import IObjectAddedEvent
from arche.interfaces import IObjectUpdatedEvent
from arche.interfaces import IObjectWillBeRemovedEvent
from arche.interfaces import IFileUploadTempStore
from arche.events import EmailValidatedEvent
from arche.interfaces import IUser


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

def delegate_email_validated(context, event):
    """ When a user object is added to the resource tree,
        send an IEmailValidatedEvent on that context if
        the email address is set as valid.

        This is needed so scripts and similar pick this up.
    """
    if context.email_validated == True:
        reg = get_current_registry()
        reg.notify(EmailValidatedEvent(context))

def includeme(config):
    config.add_subscriber(propagate_added_subscriber, [IFolder, IObjectAddedEvent])
    config.add_subscriber(propagate_will_be_removed_subscriber, [IFolder, IObjectWillBeRemovedEvent])
    config.add_subscriber(clear_upload_storage, [IBase, IObjectAddedEvent])
    config.add_subscriber(clear_upload_storage, [IBase, IObjectUpdatedEvent])
    config.add_subscriber(delegate_email_validated, [IUser, IObjectAddedEvent])
