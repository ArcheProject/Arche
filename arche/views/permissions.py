from peppercorn import parse

from arche import _
from arche.fanstatic_lib import pure_js
from arche.security import PERM_MANAGE_USERS
from arche.security import get_roles
from arche.views.base import BaseView


class PermissionsForm(BaseView):

    def __call__(self):
        pure_js.need()
        return {'roles': get_roles(registry = self.request.registry, assignable = True).values()}


class PermissionsJSON(BaseView):

    def __call__(self):
        return {'principals': self.get_principals()}

    def get_principals(self):
        roles = get_roles(registry = self.request.registry)
        principals = []
        for (k, v) in self.context.local_roles.items():
            row = {'name': k}
            for role in roles:
                if roles[role].assignable:
                    row[str(role)] = role in v
            principals.append(row)
        return principals


class HandlePermissions(PermissionsJSON):

    def __call__(self):
        appstruct = parse(self.request.POST.items())
        appstruct.pop('csrf_token', None)
        method = appstruct.pop('method', None)
        response = {}
        if method == 'add':
            principal = appstruct['principal']
            if principal.startswith('group:'):
                if principal in self.root['groups']:
                    self.context.local_roles[principal] = appstruct['roles']
                else:
                    response['errors'] = {'principal': _("That GroupID don't exist")}
            else:
                if principal in self.root['users']:
                    self.context.local_roles[principal] = appstruct['roles']
                else:
                    response['errors'] = {'principal': _("That UserID don't exist")}
        elif method == 'set':
            self.context.local_roles = appstruct
            #Validate, return a proper response
        else:
            pass
            #response['errors']?
        response['principals'] = self.get_principals()
        return response


def includeme(config):
    config.add_view(PermissionsForm,
                    name = 'permissions',
                    context = 'arche.interfaces.IContent',
                    permission = PERM_MANAGE_USERS,
                    renderer = 'arche:templates/permissions.pt')
    config.add_view(PermissionsJSON,
                    name = 'permissions.json',
                    context = 'arche.interfaces.IContent',
                    permission = PERM_MANAGE_USERS,
                    renderer = 'json')
    config.add_view(HandlePermissions,
                    check_csrf = True,
                    request_method = 'POST',
                    name = 'permissions.json',
                    context = 'arche.interfaces.IContent',
                    permission = PERM_MANAGE_USERS,
                    renderer = 'json')
