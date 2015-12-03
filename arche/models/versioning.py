from UserDict import IterableUserDict

from BTrees.LOBTree import LOBTree
from BTrees.OOBTree import OOBTree
from persistent.persistence import Persistent
from pyramid.threadlocal import get_current_registry
from pyramid.threadlocal import get_current_request
from six import string_types
from zope.component import adapter
from zope.interface import Interface
from zope.interface import providedBy
from zope.interface.declarations import implementer

from arche.interfaces import IRevisions
from arche.utils import utcnow
from arche.interfaces import ITrackRevisions
from arche.interfaces import IObjectUpdatedEvent
from arche.interfaces import IObjectAddedEvent


@adapter(ITrackRevisions)
@implementer(IRevisions)
class Revisions(object):

    def __init__(self, context):
        self.context = context
        self.data = getattr(self.context, '_revisions', {})

    def new(self, event, request = None):
        """ Create a new revision based on an IObjectUpdatedEvent
        """
        _marker = object()
        if request is None: #pragma: no coverage
            request = get_current_request()
        try:
            revisions = self.context._revisions
        except AttributeError:
            revisions = self.context._revisions = LOBTree()
            self.data = revisions
        tracked = self.get_tracked_attributes(request.registry)
        data = {}
        if getattr(event, 'changed', None) is None:
            check_attrs = tracked
        else:
            check_attrs = event.changed
        for attr in check_attrs:
            if attr in tracked:
                attr_result = getattr(self.context, attr, _marker)
                if attr_result != _marker:
                    data[attr] = attr_result
        if data:
            key = self._next_key()
            revisions[key] = rev = Revision(request.authenticated_userid, data, key)
            return rev

    def get_tracked_attributes(self, registry = None):
        vr = get_versioning(registry)
        found = set()
        if hasattr(self.context, 'type_name'):
            found.update(vr.get(self.context.type_name, ()))
        for iface in providedBy(self.context):
            found.update(vr.get(iface, ()))
        return found

    def get_revisions(self, attribute, limit = 5, matching = None):
        i = 0
        for rev in reversed(self.values()):
            if i >= limit:
                raise StopIteration()
            if attribute in rev:
                if matching is not None and rev.data[attribute] != matching:
                    continue
                i += 1
                yield rev

    def _next_key(self):
        try:
            return self.context._revisions.maxKey() + 1
        except (AttributeError, ValueError):
            return 0

    def __nonzero__(self):
        return True

    def __len__(self):
        return len(self.data)

    def __setitem__(self, key, value):
        raise NotImplementedError("Use the 'new'-method instead.")

    def __delitem__(self, key):
        """ Only allow first and last key to be deleted. Having gaps in the key
            sequence might cause bad side-effects.
            (Like generators not working in a way where you can predict what's going to happen)
        """
        if key in self and key in (self.data.maxKey(), self.data.minKey()):
            del self.data[key]
        raise KeyError(key)

    def __getitem__(self, key):
        return self.data[key]

    def __contains__(self, key):
        return key in self.data

    def __iter__(self):
        return iter(self.data)

    def get(self, key, default = None):
        return self.data.get(key, default)

    def items(self):
        return self.data.items()

    def values(self):
        return self.data.values()
        
    def keys(self):
        return self.data.keys()

    def __repr__(self): #pragma: no coverage
        klass = self.__class__
        classname = '%s.%s' % (klass.__module__, klass.__name__)
        return '<%s with %s items>' % (classname, len(self))


class Revision(Persistent):
    userid = None
    timestamp = None
    id = None

    def __init__(self, userid, data, id, timestamp = None):
        if timestamp == None:
            timestamp = utcnow()
        self.userid = userid
        self.data = OOBTree(data)
        self.id = id
        self.timestamp = timestamp

    def __contains__(self, key):
        return key in self.data

    def __getitem__(self, key):
        return self.data[key]


class VersioningRegistry(IterableUserDict):
    pass


def add_versioning(config, iface_or_ctype, attributes = ()):
    if not isinstance(iface_or_ctype, string_types):
        try:
            if not issubclass(iface_or_ctype, Interface):
                raise TypeError()
        except TypeError:
            raise TypeError("%r must be an Interface or a String" % iface_or_ctype)
    versioning_reg = get_versioning(config.registry)
    if iface_or_ctype not in versioning_reg:
        versioning_reg[iface_or_ctype] = set()
    versioning_reg[iface_or_ctype].update(attributes)

def get_versioning(registry = None):
    if registry is None: #pragma: no coverage
        registry = get_current_registry()
    try:
        return registry._versioning_registry
    except AttributeError:
        vr = registry._versioning_registry = VersioningRegistry()
        return vr

def versioning_subscriber(context, event):
    revisions = IRevisions(context)
    revisions.new(event)

def includeme(config):
    """ Include versioning. """
    config.add_directive('add_versioning', add_versioning)
    config.add_subscriber(versioning_subscriber, [ITrackRevisions, IObjectAddedEvent])
    config.add_subscriber(versioning_subscriber, [ITrackRevisions, IObjectUpdatedEvent])
    config.registry.registerAdapter(Revisions)
