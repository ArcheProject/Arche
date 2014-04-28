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
from repoze.folder import Folder

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
        return self.settings.get('title', getattr(self.portlet_adapter, 'title', u''))

    @property
    def description(self):
        return self.settings.get('description', getattr(self.portlet_adapter, 'description', u''))

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

    @property
    def slot(self):
        try:
            return self.__parent__.slot
        except AttributeError:
            pass

    def render(self, context, request, view, **kw):
        return self.portlet_adapter.render(context, request, view, **kw)
        

class PortletFolder(Folder):
    """ Container for portlets. """
    __name__ = None
    __parent__ = None
    type_name = u"PortletFolder"
    type_title = _(u"Portlet folder")
    type_description = _(u"Container for portlets")
    addable_to = ()

    def __init__(self, slot):
        self.slot = slot
        super(PortletFolder, self).__init__()


class PortletSlotInfo(object):
    title = u""
    slot = u""
    layout = u""

    def __init__(self, slot, title = u"", layout = u""):
        self.slot = slot
        self.title = title
        self.layout = layout


@adapter(IContent)
@implementer(IPortletManager)
class PortletManager(IterableUserDict):
    
    def __init__(self, context):
        self.context = context
        self.data = getattr(context, '__portlets__', {})

    def __setitem__(self, key, pf):
        assert isinstance(pf, PortletFolder), u"Not a portlet forlder"
        if isinstance(self.data, dict):
            self.data = self.context.__portlets__ = OOBTree()
        self.data[key] = pf

    def add(self, slot, portlet_type, **kw):
        factory = get_content_factories()['Portlet']
        portlet = factory(portlet_type, **kw)
        if slot not in self:
            self[slot] = pf = get_content_factories()['PortletFolder'](slot)
            pf.__parent__ = self.context
        portlets = self[slot]
        portlets[portlet.uid] = portlet
        portlet.__parent__ = portlets
        return portlet

    def remove(self, slot, portlet_uid):
        self[slot].pop(portlet_uid, None)

    def render_slot(self, slot, context, request, view, **kw):
        results = []
        for portlet in self.get(slot, {}).values():
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
    config.add_content_factory(PortletFolder)
    config.add_directive('add_portlet', add_portlet)
    config.registry.registerAdapter(PortletManager)
    left_slot = PortletSlotInfo('left', title = _(u"Left"), layout = 'vertical')
    right_slot = PortletSlotInfo('right', title = _(u"Right"), layout = 'vertical')
    top_slot = PortletSlotInfo('top', title = _(u"Top"), layout = 'horizontal')
    bottom_slot = PortletSlotInfo('bottom', title = _(u"Bottom"), layout = 'horizontal')
    config.registry._portlet_slots = {'left': left_slot,
                                      'right': right_slot,
                                      'top': top_slot,
                                      'bottom': bottom_slot}
