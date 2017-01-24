from peppercorn import parse

from arche import _
from arche.fanstatic_lib import pure_js
from arche.interfaces import ILocalRoles
from arche.security import PERM_MANAGE_USERS
from arche.views.base import BaseView


class PermissionsForm(BaseView):

    def __call__(self):
        pure_js.need()
        roles = self.context.local_roles.get_assignable(registry = self.request.registry)
        return {'roles': roles.values()}


class PermissionsJSON(BaseView):

    def __call__(self):
        return {'principals': self.get_principals()}

    def get_principals(self):
        roles = self.context.local_roles.get_assignable(registry = self.request.registry)
        principals = []
        for (k, v) in self.context.local_roles.items():
            row = {'name': k, 'url': '#'}
            obj = self.principal_obj(k)
            if obj:
                row['url'] = self.request.resource_url(obj)
            for role in roles:
                row[str(role)] = role in v
            principals.append(row)
        return principals

    def principal_obj(self, principal):
        if principal.startswith('group:'):
            if principal[6:] in self.root.get('groups', ()):
                return self.root['groups'][principal[6:]]
        else:
            if principal in self.root.get('users', ()):
                return self.root['users'][principal]


class HandlePermissions(PermissionsJSON):

    def __call__(self):
        appstruct = parse(self.request.POST.items())
        appstruct.pop('csrf_token', None)
        method = appstruct.pop('method', None)
        response = {}
        if method == 'add':
            principal = appstruct['principal']
            if principal.startswith('group:'):
                if principal[6:] in self.root['groups']:
                    self.context.local_roles.add(principal, appstruct['roles'])
                else:
                    response['errors'] = {'principal': _("That GroupID don't exist")}
            else:
                if principal in self.root['users']:
                    self.context.local_roles.add(principal, appstruct['roles'])
                else:
                    response['errors'] = {'principal': _("That UserID don't exist")}
        elif method == 'set':
            self.context.local_roles.set_from_appstruct(appstruct, event=True)
            #Validate, return a proper response
        else:
            pass
            #response['errors']?
        response['principals'] = self.get_principals()
        return response


def includeme(config):
    config.add_view(PermissionsForm,
                    name = 'permissions',
                    context = ILocalRoles,
                    permission = PERM_MANAGE_USERS,
                    renderer = 'arche:templates/permissions.pt')
    config.add_view(PermissionsJSON,
                    name = 'permissions.json',
                    context = ILocalRoles,
                    permission = PERM_MANAGE_USERS,
                    renderer = 'json')
    config.add_view(HandlePermissions,
                    check_csrf = True,
                    request_method = 'POST',
                    name = 'permissions.json',
                    context = ILocalRoles,
                    permission = PERM_MANAGE_USERS,
                    renderer = 'json')
