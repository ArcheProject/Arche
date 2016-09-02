from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPFound

from arche import _
from arche.plugins.auth_sessions.interfaces import IAuthSessionData
from arche import security
from arche.interfaces import IUser
from arche.views.base import BaseForm
from arche.views.base import BaseView


class AuthSessionsView(BaseView):

    def __call__(self):
        auth_sessions = IAuthSessionData(self.request)
        inactivate = self.request.GET.get('inactivate', None)
        if inactivate:
            try:
                inactivate = int(inactivate)
                auth_sessions.inactivate(self.context.userid, inactivate)
                self.flash_messages.add(_("Logged out session ${id}",
                                          mapping = {'id': inactivate}),
                                        type = 'success')
            except ValueError:
                self.flash_messages.add(_("No active session with id: ${id}",
                                          mapping = {'id': inactivate}),
                                        type = 'danger')
            return HTTPFound(location = self.request.resource_url(self.context, 'auth_sessions'))
        return {'session_data': reversed(auth_sessions.get_data(self.context.userid)),
                'active': auth_sessions.get_active(userid = self.context.userid)}


class AddAuthSessionForm(BaseForm):
    schema_name = "add"
    type_name = "Auth"

    def appstruct(self):
        return {}

    def save_success(self, appstruct):
        asd = IAuthSessionData(self.request)
        ad = asd.new(self.context.userid, user_agent = None, **appstruct)
        msg = _("new_auth_session_details",
                default = "Authentication session created with id ${id}",
                mapping = {'id': ad.key})
        self.flash_messages.add(msg, type='success')
        return HTTPFound(location=self.request.resource_url(self.context, 'auth_sessions'))

    def cancel(self, *args):
        return HTTPFound(location=self.request.resource_url(self.context, 'auth_sessions'))
    cancel_success = cancel_failure = cancel


class EditAuthSessionForm(BaseForm):
    schema_name = "edit"
    type_name = "Auth"

    def get_ad(self):
        try:
            asession = int(self.request.subpath[0])
        except (IndexError, ValueError):
            raise HTTPNotFound()
        asd = IAuthSessionData(self.request)
        try:
            return asd.sessions[self.context.userid][asession]
        except KeyError:
            raise HTTPNotFound()

    def appstruct(self):
        ad = self.get_ad()
        appstruct = {}
        for node in self.schema:
            val = getattr(ad, node.name)
            if val != None:
                appstruct[node.name] = getattr(ad, node.name)
        return appstruct

    def save_success(self, appstruct):
        ad = self.get_ad()
        for (k, v) in appstruct.items():
            setattr(ad, k, v)
        self.flash_messages.add(self.default_success, type='success')
        return HTTPFound(location=self.request.resource_url(self.context, 'auth_sessions'))

    def cancel(self, *args):
        return HTTPFound(location=self.request.resource_url(self.context, 'auth_sessions'))
    cancel_success = cancel_failure = cancel


def includeme(config):
    config.add_view(AuthSessionsView,
                    context = IUser,
                    name = 'auth_sessions',
                    permission = security.PERM_ACCESS_AUTH_SESSIONS,
                    renderer = 'arche.plugins.auth_sessions:templates/sessions.pt')
    config.add_view(AddAuthSessionForm,
                    context = IUser,
                    name = 'add_auth_session',
                    permission = security.PERM_MANAGE_USERS,
                    renderer = 'arche:templates/form.pt')
    config.add_view(EditAuthSessionForm,
                    context = IUser,
                    name = 'edit_auth_session',
                    permission = security.PERM_MANAGE_USERS,
                    renderer = 'arche:templates/form.pt')
