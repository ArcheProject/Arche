# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyramid.view import view_config

from arche.fanstatic_lib import consent_js
from arche.interfaces import IBaseView
from arche.interfaces import IViewInitializedEvent


@view_config(name='__cookie_consent__', renderer='arche.plugins.cookie_consent:templates/consent_dialog.pt')
def cookie_consent(context, request):
    """ Set cookie_consent.path = <path> in your .ini-file to enable policy link. """
    return {
        'cookie_policy_path': request.registry.settings.get('cookie_consent.path'),
    }


def needs(view, event):
    consent_js.need()


def includeme(config):
    config.scan(__name__)
    config.add_subscriber(needs, [IBaseView, IViewInitializedEvent])
