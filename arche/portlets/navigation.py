import colander

from arche.schemas import PortletBaseSchema
from arche.portlets import PortletType
from arche import _


class NavSchema(PortletBaseSchema):
    pass


class NavigationPortlet(PortletType):
    name = u"navigation"
    schema_factory = NavSchema
    title = _(u"Navigation")


def includeme(config):
    config.registry.registerAdapter(NavigationPortlet, name = NavigationPortlet.name)
