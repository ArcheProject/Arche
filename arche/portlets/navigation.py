import colander
from pyramid.renderers import render

from arche.schemas import PortletBaseSchema
from arche.portlets import PortletType
from arche import _


class NavSchema(PortletBaseSchema):
    pass


class NavigationPortlet(PortletType):
    name = u"navigation"
    schema_factory = NavSchema
    title = _(u"Navigation")

    def render(self, context, request, view, **kwargs):
        if context is view.root:
            return
        contents = view.get_local_nav_objects(context)
        if not contents:
            return
        return render("arche:templates/portlets/navigation.pt", {'title': self.title, 'contents': contents}, request = request)


def includeme(config):
    config.add_portlet(NavigationPortlet)
