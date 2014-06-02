import colander

from pyramid.renderers import render


from arche.portlets import PortletType
from arche import _


class LoginSettingsSchema(colander.Schema):
    pass #FIXME


class LoginPortlet(PortletType): 
    name = u"login"
    schema_factory = LoginSettingsSchema
    title = _(u"Authentication")

    def render(self, context, request, view, **kwargs):
        if request.authenticated_userid:
            return
        return render("arche:templates/portlets/login.pt",
                      {'portlet': self.portlet, 'view': view},
                      request = request)


def includeme(config):
    config.add_portlet(LoginPortlet)
