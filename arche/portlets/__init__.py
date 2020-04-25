from __future__ import unicode_literals

from uuid import uuid4

from BTrees.OOBTree import OOBTree
from persistent import Persistent
from pyramid.threadlocal import get_current_registry
from repoze.folder import Folder
from zope.component import ComponentLookupError
from zope.component import adapter
from zope.interface import implementer
from zope.interface.verify import verifyClass
from six import text_type

from arche import _
from arche import logger
from arche.compat import IterableUserDict
from arche.interfaces import IContent
from arche.interfaces import IPortlet
from arche.interfaces import IPortletManager
from arche.interfaces import IPortletType
from arche.utils import get_content_factories


@adapter(IPortlet)
@implementer(IPortletType)
class PortletType(object):
    name = ""
    schema_factory = None
    title = ""
    tpl = ""
    
    def __init__(self, portlet):
        self.portlet = portlet

    def visible(self, context, request, view, **kwargs):
        # Must be implemented by subclass!
        return False

    def render(self, context, request, view, **kwargs):
        return u""

    @property
    def context(self):
        """ The context this portlet was originaly created at.
            (I.e. the place where the PortletFolders will be)
            It doesn't have to be the same context as the current request.
        """
        return self.portlet.__parent__.__parent__


class BrokenPortletType(PortletType):

    @property
    def title(self):
        return "<Broken Portlet: '%s'>" % self.name

    def __init__(self, portlet, name):
        self.portlet = portlet
        self.name = name


@implementer(IPortlet)
class Portlet(Persistent):
    __name__ = None
    __parent__ = None
    type_name = u"Portlet"
    type_title = _(u"Portlet")
    type_description = _(u"A mini view within another view")
    portlet_type = u""
    add_permission = "Add %s" % type_name
    enabled = True

    def __init__(self, portlet_type, **kw):
        self.uid = text_type(uuid4())
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
        try:
            return reg.getAdapter(self, IPortletType, name = self.portlet_type)
        except ComponentLookupError:
            return BrokenPortletType(self, self.portlet_type)

    @property
    def slot(self):
        try:
            return self.__parent__.slot
        except AttributeError:
            pass

    def render(self, context, request, view, **kw):
        try:
            return self.portlet_adapter.render(context, request, view, **kw)
        except ComponentLookupError:
            logger.error("portlet %r not found for context %r" % (self.portlet_type, context))
        return ""
        

class PortletFolder(Folder):
    """ Container for portlets. """
    __name__ = None
    __parent__ = None
    type_name = u"PortletFolder"
    type_title = _(u"Portlet folder")
    type_description = _(u"Container for portlets")
    add_permission = None

    def __init__(self, slot):
        self.slot = slot
        self.order = () #Initializing order makes the folder keep track of it.
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

    def get_portlets(self, slot, portlet_type = None):
        results = []
        for portlet in self.get(slot, {}).values():
            if portlet_type and portlet_type != portlet.portlet_type:
                continue
            results.append(portlet)
        return results

    def remove(self, slot, portlet_uid):
        self[slot].pop(portlet_uid, None)

    def visible(self, slot, context, request, view, **kw):
        """ Check if any portlet within this slot is registered as visible.
        """
        for portlet in self.get(slot, {}).values():
            if portlet.enabled:
                portlet_type = portlet.portlet_adapter
                if portlet_type.visible(context, request, view, **kw):
                    return True
        return False

    def render_slot(self, slot, context, request, view, **kw):
        results = []
        for portlet in self.get(slot, {}).values():
            if portlet.enabled:
                output = portlet.render(context, request, view, **kw)
                if output:
                    results.append(output)
        return results

    def __repr__(self):
        return "<%s with %r>" % (self.__class__.__name__, self.keys())

    def __nonzero__(self):
        return True
    __bool__ = __nonzero__


def get_portlet_slots(registry = None):
    if registry is None:
        registry = get_current_registry()
    return registry.portlet_slots

def get_portlet_manager(context, registry = None):
    if registry is None:
        registry = get_current_registry()
    return registry.queryAdapter(context, IPortletManager)    


def get_available_portlets(registry = None):
    if registry is None:
        registry = get_current_registry()
    return [(x.name, x.factory.title) for x in registry.registeredAdapters() if x.provided == IPortletType]


def add_portlet(config, portlet):
    verifyClass(IPortletType, portlet)
    config.registry.registerAdapter(portlet, name = portlet.name)


def add_portlet_slot(config, name, title = "", layout = ""):
    config.registry.portlet_slots[name] = PortletSlotInfo(name, title = title, layout = layout)


def includeme(config):
    config.add_content_factory(Portlet)
    config.add_content_factory(PortletFolder)
    config.add_directive('add_portlet', add_portlet)
    config.add_directive('add_portlet_slot', add_portlet_slot)
    config.registry.portlet_slots = {}
    config.registry.registerAdapter(PortletManager, provided=IPortletManager)
    config.add_portlet_slot('left', title = _("Left"), layout = 'vertical')
    config.add_portlet_slot('right', title = _("Right"), layout = 'vertical')
    config.add_portlet_slot('top', title = _("Top"), layout = 'horizontal')
    config.add_portlet_slot('bottom', title = _("Bottom"), layout = 'horizontal')
