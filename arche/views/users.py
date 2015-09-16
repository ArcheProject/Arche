from __future__ import unicode_literals

from pyramid.decorator import reify

from arche import _
from arche import security
from arche.fanstatic_lib import pure_js
from arche.interfaces import IDateTimeHandler
from arche.interfaces import IJSONData
from arche.views.base import BaseView


class UsersView(BaseView):
    """ A table listing of all users.
    """

    def __call__(self):
        pure_js.need()
        return {}


class JSONUsers(BaseView):

    @reify
    def dt_handler(self):
        return IDateTimeHandler(self.request)

    def __call__(self):
        results = []
        for obj in self.context.values():
            if self.request.has_permission(security.PERM_VIEW, obj):
                results.append(obj)
        response = {}
        response['items'] = self.json_format_objects(results)
        return response

    def json_format_objects(self, items):
        res = []
        for obj in items:
            adapted = IJSONData(obj)
            res.append(adapted(self.request, dt_formater = self.dt_handler.format_relative, attrs = ('userid', 'email', 'first_name', 'last_name', 'email_validated')))
        return res


def includeme(config):
    config.add_view(UsersView,
                    name = 'view',
                    permission = security.PERM_MANAGE_USERS,
                    renderer = "arche:templates/content/users_table.pt",
                    context = 'arche.interfaces.IUsers')
    config.add_view(JSONUsers,
                    name = 'users.json',
                    permission = security.PERM_MANAGE_USERS,
                    renderer = "json",
                    context = 'arche.interfaces.IUsers')
