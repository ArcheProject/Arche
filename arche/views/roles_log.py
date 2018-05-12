# -*- coding: utf-8 -*-
from json import loads
from logging import FileHandler
from os.path import isfile

from arche.interfaces import IRolesCommitLogger, ILocalRoles
from arche.security import PERM_MANAGE_SYSTEM
from arche.views.base import BaseForm
from deform import Button
from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPFound
from six import string_types

from arche import _


class FilterExcluded(Exception):
    """ Raised when filter doesn't match."""


class RolesLogView(BaseForm):
    buttons = (Button('parse', title=_("Parse")),)
    type_name = 'Auth'
    schema_name = 'view_roles_log'
    # Filter with the easiest check first
    filter_names = (
        "only_current_context",
        "view_contains",
        "done_by_userid",
        "regarding_userid",
        "regarding_role",
    )

    def __call__(self):
        self._cached_uids = {}
        if not self.logger_filename:
            self.flash_messages.add(
                "No FileHandler seems to be configured for the RolesCommitLogger.",
                type='danger',
            )
            return HTTPFound(location=self.request.resource_url(self.context))
        if not isfile(self.logger_filename):
            self.flash_messages.add(
                "RolesCommitLogger has a FileHandler, but the file it points to doesn't exist %s" % self.logger_filename,
                type='danger',
            )
            return HTTPFound(location=self.request.resource_url(self.context))
        return super(RolesLogView, self).__call__()

    @reify
    def logger_filename(self):
        rcl = IRolesCommitLogger(self.request)
        for handler in rcl.logger.handlers:
            if isinstance(handler, FileHandler):
                return handler.baseFilename

    def parse_success(self, appstruct):
        filter_methods = self.build_filter(appstruct)
        # Max matches?
        output_rows = []
        for rowdata in parse_roles_logfile(self.logger_filename):
            try:
                for method in filter_methods:
                    method(rowdata, appstruct)
                # No complaints from filter
                output_rows.append(rowdata)
            except FilterExcluded as exc:
                pass
        return {'output_rows': output_rows, 'only_context': appstruct['only_current_context']}

    def build_filter(self, appstruct):
        methods = []
        for k in self.filter_names:
            if appstruct.get(k):
                methods.append(getattr(self, 'filter_%s' % k))
        return methods

    def filter_only_current_context(self, data, appstruct):
        if self.context.uid not in data['contexts']:
            raise FilterExcluded("Not current context")
        # Remove rows that aren't relevant
        for uid in tuple(data['contexts']):
            if self.context.uid != uid:
                data['contexts'].pop(uid)

    def filter_regarding_userid(self, data, appstruct):
        regarding_userid = appstruct['regarding_userid']
        for uid in tuple(data['contexts']):
            if regarding_userid not in data['contexts'][uid]:
                data['contexts'].pop(uid)
        if not data['contexts']:
            raise FilterExcluded("Regarding userid excluded")

    def filter_done_by_userid(self, data, appstruct):
        if data['userid'] != appstruct['done_by_userid']:
            raise FilterExcluded("Done by userid excluded")

    def filter_regarding_role(self, data, appstruct):
        role = appstruct['regarding_role']
        for uid in tuple(data['contexts']):
            for (userid, roledata) in data['contexts'][uid].items():
                roles = set()
                for rdata in roledata.values():
                    roles.extend(rdata)
                if role not in roles:
                    data['contexts'][uid].pop(userid)
            if not data['contexts'][uid]:
                data['contexts'].pop(uid)
        if not data['contexts']:
            raise FilterExcluded("regarding role excluded")

    def filter_view_contains(self, data, appstruct):
        if appstruct['view_contains'] not in data['url']:
            raise FilterExcluded("URL didn't match")

    def get_uid(self, uid):
        try:
            return self._cached_uids[uid]
        except KeyError:
            # Permission check shouldn't be relevant here, this view should never be accessed
            # by anyone else than system administrators, since it may contain sensitive information.
            obj = self.request.resolve_uid(uid, perm=None)
            self._cached_uids[uid] = obj
            return obj

    def get_role_title(self, role):
        if isinstance(role, string_types):
            return self.request.registry.roles[role].title
        return role.title


def parse_roles_logfile(fname, start=0, stop=None):
    with open(fname) as f:
        for i, line in enumerate(f):
            if stop and stop < i:
                break
            if i >= start:
                yield loads(line)


def includeme(config):
    if config.registry.settings.get('arche.log_roles'):
        config.add_view(RolesLogView, context=ILocalRoles,
                        name='local_roles_log', permission=PERM_MANAGE_SYSTEM,
                        renderer='arche:templates/system/roles_log.pt')
