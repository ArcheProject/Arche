from pyramid.renderers import render

from arche.portlets import PortletType
from arche import _


class BylinePortlet(PortletType):
    name = u"byline"
    title = _(u"Byline")

    def render(self, context, request, view, **kwargs):
        if not getattr(context, 'show_byline', False):
            return
        creator = getattr(context, 'creator', None)
        if not creator:
            return
        out = u""
        for uid in creator:
            #Catalog search returns a generator
            for profile in view.catalog_search(resolve = True, uid = uid):
                out += render("arche:templates/portlets/byline.pt",
                              {'profile': profile, 'portlet': self.portlet, 'view': view},
                              request = request)
        return out

def includeme(config):
    config.add_portlet(BylinePortlet)
