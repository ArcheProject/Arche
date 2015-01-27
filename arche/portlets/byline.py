from __future__ import unicode_literals

from pyramid.renderers import render

from arche.portlets import PortletType
from arche import _


class BylinePortlet(PortletType):
    name = "byline"
    title = _("Byline")

    def render(self, context, request, view, **kwargs):
        if not getattr(context, 'show_byline', False):
            return
        creator = getattr(context, 'creator', ())
        out = ""
        for userid in creator:
            #Catalog search returns a generator
            for profile in view.catalog_search(resolve = True, userid = userid):
                out += render("arche:templates/portlets/byline.pt",
                              {'profile': profile, 'portlet': self.portlet, 'view': view},
                              request = request)
        return out

def includeme(config):
    config.add_portlet(BylinePortlet)
