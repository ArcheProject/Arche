# -*- coding: utf-8 -*-
import deform
from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import render
from pyramid.response import Response
from pyramid.security import forget
from pyramid.security import NO_PERMISSION_REQUIRED

from arche.plugins.tos.exceptions import TermsNotAccepted
from arche.security import PERM_VIEW
from arche.interfaces import IFlashMessages
from arche.interfaces import IRoot
from arche.interfaces import IUser
from arche.plugins.tos.interfaces import ITOS
from arche.plugins.tos.interfaces import ITOSManager
from arche.views.base import BaseForm
from arche.views.base import button_cancel
from arche.views.base import BaseView
from arche import _


class TOSForm(BaseForm):
    type_name = 'TOS'
    schema_name = 'agree'
    title = _("Terms of service")
    buttons = (deform.Button('agree', title=_("Agree")),)

    def __call__(self):
        print self.request.params
        return super(TOSForm, self).__call__()

    @reify
    def tos_manager(self):
        return ITOSManager(self.request)

    @property
    def use_ajax(self):
        return self.request.is_xhr

    def before_fields(self):
        values = {'tos_items': self.tos_manager.find_tos()}
        return render('arche.plugins.tos:templates/tos_listing.pt', values, request=self.request)

    def agree_success(self, appstruct):
        self.flash_messages.add(_("Thank you!"), type='success')
        self.tos_manager.agree_to(self.tos_manager.find_tos())
        if self.use_ajax:
            return Response(render("arche:templates/deform/destroy_modal.pt", {}, request=self.request))
        return HTTPFound(location=self.request.resource_url(self.context))


class AgreedTOSView(BaseView):

    @reify
    def tos_manager(self):
        return ITOSManager(self.request)

    def __call__(self):
        active = []
        inactive = []
        for uid, date in self.tos_manager.agreed_tos.items():
            tos = self.request.resolve_uid(uid, perm=None)
            if tos:
                if tos.wf_state == 'enabled':
                    active.append((tos, date))
                else:
                    inactive.append((tos, date))
        active = sorted(active, key=lambda x: x[1])
        inactive = sorted(inactive, key=lambda x: x[1])
        return {'active_tos': active, 'inactive_tos': inactive}

# class RevokeAgreementForm(BaseForm):
#     type_name = 'TOS'
#     schema_name = 'revoke'
#     title = _("Revoke agreement")
#
#     @property
#     def buttons(self):
#         kwargs = {}
#         if self.context.wf_state == 'enabled':
#             kwargs['css_class'] = 'btn-danger'
#         return (deform.Button('revoke', title=_("Revoke"), **kwargs), button_cancel)
#
#     @reify
#     def tos_manager(self):
#         return ITOSManager(self.request)
#
#     @property
#     def use_ajax(self):
#         return self.request.is_xhr
#
#     def before_fields(self):
#         # List the consequences of revoking this agreement
#         values = {}
#         return render('arche.plugins.tos:templates/revoke_tos_consequence.pt', values, request=self.request)
#
#
#
#     #FIXME: Do this properly
#     def revoke_success(self, appstruct):
#         agreed_tos = self.tos_manager.agreed_tos
#         if self.context.uid in agreed_tos:
#             del agreed_tos[self.context.uid]
#             self.flash_messages.add(_("REVOKED!"), type='danger', require_commit=False)
#         return self.relocate_response(self.request.resource_url(self.profile, 'agreed_tos'))
#
#
#         if self.use_ajax:
#             body = """
#
#             <script type="text/javascript">
# //              arche.destroy_modal();
# //              arche.load_flash_messages(); //If any from modal interaction
#               document.location = '%s'
#             </script>""" % self.request.resource_url(self.profile, 'agreed_tos')
#             return Response(body)
#             #return Response(render("arche:templates/deform/destroy_modal.pt", {}, request=self.request))
#         return HTTPFound(location=self.request.resource_url(self.profile))
#
#     def cancel_success(self, *args):
#         return self.relocate_response(self.request.resource_url(self.profile, 'agreed_tos'))
#         #if self.use_ajax:
#         #    return Response(render("arche:templates/deform/destroy_modal.pt", {}, request=self.request))
#         #return HTTPFound(location=)
#     cancel_failure = cancel_success


def terms_not_accepted(context, request):
    headers = forget(request)
    request.session.invalidate()
    fm = IFlashMessages(request)
    fm.add(_("You need to accept the terms to use this site."),
           type='danger', require_commit=False, auto_destruct=False)
    # Context is the exception
    return HTTPFound(location = request.resource_url(request.root),
                     headers = headers)


def includeme(config):
    config.add_view(
        TOSForm,
        context=IRoot,
        name='tos_form',
        permission=PERM_VIEW,
        renderer='arche:templates/form.pt'
    )
    config.add_view(
        AgreedTOSView,
        context=IUser,
        name='agreed_tos',
        permission=PERM_VIEW,
        renderer='arche.plugins.tos:templates/agreed_tos.pt',
    )
    # config.add_view(
    #     RevokeAgreementForm,
    #     context=ITOS,
    #     name='revoke_agreement',
    #     permission=NO_PERMISSION_REQUIRED,
    #     renderer='arche:templates/form.pt'
    # )
    config.add_exception_view(
        terms_not_accepted,
        context=TermsNotAccepted
    )
