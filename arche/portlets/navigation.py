import colander
from pyramid.renderers import render

from arche.portlets import PortletType
from arche import _


class NavSchema(colander.Schema):
    pass #FIXME


class NavigationPortlet(PortletType):
    name = u"navigation"
    schema_factory = NavSchema
    title = _(u"Navigation")
    tpl = "arche:templates/portlets/navigation.pt"

    def render(self, context, request, view, **kwargs):
        if context is view.root:
            return
        contents = tuple(view.get_local_nav_objects(context))
        if not contents:
            return
        return render(self.tpl,
                      {'title': self.title, 'contents': contents, 'portlet': self.portlet},
                      request = request)


def includeme(config):
    config.add_portlet(NavigationPortlet)
