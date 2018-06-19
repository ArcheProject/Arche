# -*- coding: utf-8 -*-
from datetime import timedelta
from logging import getLogger

from arche.security import PERM_MANAGE_SYSTEM
from arche.utils import utcnow, AttributeAnnotations
from pyramid.decorator import reify
from pyramid.interfaces import IRequest
from repoze.catalog.query import Eq
from zope.component import adapter
from zope.interface import implementer

from arche.fanstatic_lib import terms_modal
from arche.interfaces import IBaseView
from arche.interfaces import IUser
from arche.interfaces import IViewInitializedEvent
from arche.plugins.tos.interfaces import IAgreedTOS
from arche.plugins.tos.interfaces import ITOSManager
from arche.plugins.tos.exceptions import TermsNeedAcceptance
from arche.plugins.tos.exceptions import TermsNotAccepted
from arche import _


logger = getLogger(__name__)


@implementer(ITOSManager)
@adapter(IRequest)
class TOSManager(object):
    """ Checks for registered schemas with the type_name Terms.
        Any schema registered there must be agreed upon to be valid.

        Terms can also have versions.
    """
    grace_seconds = 60*10
    check_interval = 60*60*24
    logger = logger # Testing injection

    def __init__(self, request):
        self.request = request

    def check_terms(self):
        if self.needs_check():
            print("CHECK")
            # Skip check for admins
            if not self.request.has_permission(PERM_MANAGE_SYSTEM, self.request.root):
                # Find TOS that needs to be accepted
                for tos in self.find_tos():
                    if tos.uid not in self.agreed_tos:
                        self.logger.debug("Terms need acceptance: %s", tos)
                        self.check_grace_period()
                        raise TermsNeedAcceptance("TOS UID need acceptance: %s" % tos.uid)
            self.mark_checked()

    def needs_check(self):
        try:
            return self.request.session['tos_check_again_at'] < utcnow()
        except KeyError:
            return True

    def mark_checked(self):
        self.request.session['tos_check_again_at'] = utcnow() + timedelta(seconds = self.check_interval)
        self.request.session.changed()
        self.logger.debug("%s mark terms checked", self.request.authenticated_userid)

    def check_grace_period(self):
        sess = self.request.session
        if 'tos_grace_period_expires' not in self.request.session:
            self.logger.debug("%s started grace period of %s seconds",
                              self.request.authenticated_userid,
                              self.grace_seconds)
            sess['tos_grace_period_expires'] = utcnow() + timedelta(seconds = self.grace_seconds)
        if utcnow() > sess['tos_grace_period_expires']:
            raise TermsNotAccepted()

    def clear_grace_period(self):
        if 'tos_grace_period_expires' in self.request.session:
            del self.request.session['tos_grace_period_expires']
            self.request.session.changed()

    def find_tos(self):
        query = Eq('type_name', 'TOS') & Eq('wf_state', 'enabled')
        # The date query did not work as expected for me
        # Investigate this more! /rharms
        #Le('date', timegm(utcnow().date().timetuple()))
        docids = self.request.root.catalog.query(query)[1]
        today = utcnow().date()
        for tos in self.request.resolve_docids(docids, perm=None):
            # The language aspect
            if tos.lang and tos.lang != self.request.localizer.locale_name:
                continue
            if today >= tos.date and tos.uid not in self.agreed_tos:
                yield tos

    def agree_to(self, seq):
        for tos in seq:
            self.agreed_tos.accept_tos(tos.uid)
        self.clear_grace_period()

    @reify
    def agreed_tos(self):
        return IAgreedTOS(self.request.profile)


@adapter(IUser)
@implementer(IAgreedTOS)
class AgreedTOS(AttributeAnnotations):
    """ Handles a named storage for keys/values.
        UID of agreed terms will be key, and value will be a date.
    """
    attr_name = '_agreed_tos'

    def accept_tos(self, uid):
        self[uid] = utcnow().date()


def check_terms(view, event):
    request = view.request
    # Should not be used for xhr requests
    if request.is_xhr:
        return
    # Only show for authenticated
    if not request.authenticated_userid:
        return
    if request.view_name == 'tos_form':
        return
    terms_manager = ITOSManager(request)
    try:
        # If the grace period expired, this will raise an uncaught TermsNotAccepted
        return terms_manager.check_terms()
    except TermsNeedAcceptance:
        terms_modal.need()
        return


def includeme(config):
    """
    Include components

    In your paster ini file, add the following keys to customize:
    # Number of seconds to wait before kicking out users that haven't agreed
    arche.tos.grace_seconds = <int>
    # Number of seconds to wait between each check
    arche.tos.check_interval = <int>
    """
    settings = config.registry.settings
    prefix = 'arche.tos.%s'
    for k in ('grace_seconds', 'check_interval'):
        key = prefix % k
        if key in settings:
            val = int(settings[key])
            setattr(TOSManager, k, val)
    config.registry.registerAdapter(TOSManager)
    config.registry.registerAdapter(AgreedTOS)
    config.add_subscriber(check_terms, [IBaseView, IViewInitializedEvent])
