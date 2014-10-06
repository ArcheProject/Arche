from zope.component.event import objectEventNotify
from repoze.folder.events import ObjectAddedEvent
from repoze.folder.events import ObjectWillBeRemovedEvent

from arche.interfaces import IFolder
from arche.interfaces import IObjectAddedEvent
from arche.interfaces import IObjectWillBeRemovedEvent



def propagate_added_subscriber(context, event):
    for obj in context.values():
        objectEventNotify(ObjectAddedEvent(obj, context, obj.__name__))

def propagate_will_be_removed_subscriber(context, event):
    for obj in context.values():
        objectEventNotify(ObjectWillBeRemovedEvent(obj, context, obj.__name__))


def includeme(config):
    config.add_subscriber(propagate_added_subscriber, [IFolder, IObjectAddedEvent])
    config.add_subscriber(propagate_will_be_removed_subscriber, [IFolder, IObjectWillBeRemovedEvent])
