from UserDict import IterableUserDict
from uuid import uuid4

from zope.interface import implementer
from zope.interface.verify import verifyClass
from zope.component import adapter
from zope.component import ComponentLookupError
from persistent import Persistent
from persistent.list import PersistentList
from BTrees.OOBTree import OOBTree
from pyramid.threadlocal import get_current_registry

from arche.interfaces import IPortlet
from arche.interfaces import IPortletType
from arche.interfaces import IPortletManager
from arche.interfaces import IContent
from arche.utils import get_content_factories
#from arche.resources import Bare
from arche import _


@adapter(IPortlet)
@implementer(IPortletType)
class PortletType(object):
    name = u""
    schema_factory = None
    title = u""
    
    def __init__(self, portlet):
        self.portlet = portlet

    def render(self, context, request, view, **kwargs):
        return u""


@implementer(IPortlet)
class Portlet(Persistent):
    __name__ = None
    __parent__ = None
    type_name = u"Portlet"
    type_title = _(u"Portlet")
    type_description = _(u"A mini view rendered ")
    portlet_type = u""
    addable_to = ()
    add_permission = "Add %s" % type_name

    def __init__(self, portlet_type, **kw):
        self.uid = unicode(uuid4())
        self.portlet_type = portlet_type
        self.__settings__ = OOBTree()
        settings = kw.pop('settings', {})
        self.settings = settings
        self.__dict__.update(**kw)
        super(Portlet, self).__init__()

    @property
    def title(self):
        return self.settings.get('title', u'')

    @property
    def description(self):
        return self.settings.get('description', u'')

    @property
    def settings(self):
        return self.__settings__

    @settings.setter
    def settings(self, value):
        self.__settings__.clear()
        self.__settings__.update(value)

    @property
    def schema_factory(self):
        return self.portlet_adapter.schema_factory

    @property
    def portlet_adapter(self):
        reg = get_current_registry()
        return reg.getAdapter(self, IPortletType, name = self.portlet_type)

    def render(self, context, request, view, **kw):
        return self.portlet_adapter.render(context, request, view, **kw)
        

@adapter(IContent)
@implementer(IPortletManager)
class PortletManager(IterableUserDict):
    
    def __init__(self, context):
        self.context = context
        if not hasattr(context, '__portlets__'):
            context.__portlets__ = OOBTree()
        self.data = context.__portlets__

    def add(self, slot, portlet_type, **kw):
        factory = get_content_factories()['Portlet']
        portlet = factory(portlet_type, **kw)
        slot_registry = self.setdefault(slot, PersistentList())
        slot_registry.append(portlet)
        return portlet

    def remove(self, slot, portlet_uid):
        slot_registry = self.get(slot, ())
        for portlet in slot_registry:
            if portlet.uid == portlet_uid:
                slot_registry.remove(portlet)

    def render_slot(self, slot, context, request, view, **kw):
        results = []
        for portlet in self.get(slot, ()):
            output = portlet.render(context, request, view, **kw)
            if output:
                results.append(output)
        return results


def get_portlet_slots(registry = None):
    if registry is None:
        registry = get_current_registry()
    return registry._portlet_slots

def get_portlet_manager(context, registry = None):
    if registry is None:
        registry = get_current_registry()
    return registry.queryAdapter(context, IPortletManager)    

def get_available_portlets(registry = None):
    if registry is None:
        registry = get_current_registry()
    return [(x.name, x.name) for x in registry.registeredAdapters() if x.provided == IPortletType]

def add_portlet(config, portlet):
    verifyClass(IPortletType, portlet)
    config.registry.registerAdapter(portlet, name = portlet.name)

def includeme(config):
    config.add_content_factory(Portlet)
    config.add_directive('add_portlet', add_portlet)
    config.registry.registerAdapter(PortletManager)
    config.registry._portlet_slots = {'left': _(u"Left"), 'right': _(u"Right"), 'top': _(u"Top"), 'bottom': _(u"Bottom")}
