from zope.interface import implementer
from repoze.folder.events import (ObjectAddedEvent,
                                  ObjectWillBeRemovedEvent) #API

from arche.interfaces import IObjectUpdatedEvent


@implementer(IObjectUpdatedEvent)
class ObjectUpdatedEvent(object):
    """ When an object has been updated in some way.
    """
    object = None
    changed = frozenset()
    
    def __init__(self, _object, changed = ()):
        self.object = _object
        self.changed = set(changed)
