from pyramid.renderers import render

from arche.portlets import PortletType
from arche import _


class BylinePortlet(PortletType):
    name = u"byline"
    title = _(u"Byline")

    def render(self, context, request, view, **kwargs):
        if not getattr(context, 'show_byline', False):
            return
        #FIXME: creator should be an iterable later on!
        creator = getattr(context, 'creator', None)
        if creator in view.root['users']:
            profile = view.root['users'][creator]
            return render("arche:templates/portlets/byline.pt",
                          {'profile': profile, 'portlet': self.portlet, 'view': view},
                          request = request)


def includeme(config):
    config.add_portlet(BylinePortlet)
