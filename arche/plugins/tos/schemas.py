# -*- coding: utf-8 -*-
from arche import _

import colander
import deform

from arche.schemas import maybe_modal_form, default_now
from arche.validators import deferred_current_password_validator


def _return(value):
    return value == True  # Will be interpreted as failed check by Function method.


class TOSAgreeSchema(colander.Schema):
    widget = maybe_modal_form
    agree_check = colander.SchemaNode(
        colander.Bool(),
        title=_("I agree to the terms stated above"),
        validator=colander.Function(_return, _("You must agree to the terms to use this site."))
    )


TYPED_REVOKE_SENTENCE = _("I understand the consequences")


@colander.deferred
class TypedRevokeValidator(object):

    def __init__(self, node, kw):
        self.request = kw['request']

    def __call__(self, node, value):
        if self.request.localizer.translate(TYPED_REVOKE_SENTENCE) != value:
            raise colander.Invalid(node, _("Wrong sentence"))


@colander.deferred
def typed_revoke_description(node, kw):
    request = kw['request']
    return _("Type '${sentence}' to confirm that you want to do this.",
             mapping = {'sentence': request.localizer.translate(TYPED_REVOKE_SENTENCE)})


class TOSRevokeSchema(colander.Schema):
    widget = maybe_modal_form

    typed_revoke = colander.SchemaNode(
        colander.String(),
        title=_("Type confirmation"),
        description=typed_revoke_description,
        validator=TypedRevokeValidator,
    )
    checked_revoke = colander.SchemaNode(
        colander.Bool(),
        title = _("I understand the consequences and want to revoke my agreement."),
        validator=colander.Function(_return, _("Read above and tick here if you want to do this."))
    )
    current_password =colander.SchemaNode(
        colander.String(),
        title = _("Password check due to severe consequences of revoking this"),
        widget=deform.widget.PasswordWidget(size=20),
        validator=deferred_current_password_validator,
    )

    def after_bind(self, schema, kw):
        context = kw['context']
        request = kw['request']
        remove_fields = set()
        # If current user doesn't have a password, we can't really check against that
        if not request.profile.password:
            remove_fields.add('current_password')
        # Don't enforce fields on inactive TOS
        if context.wf_state == 'enabled':
            if not context.check_password_on_revoke:
                remove_fields.add('current_password')
            if not context.check_typed_on_revoke:
                remove_fields.add('typed_revoke')
        else:
            remove_fields.update(['current_password', 'typed_revoke'])
        if 'typed_revoke' not in remove_fields:
            remove_fields.add('checked_revoke')
        for k in remove_fields:
            if k in schema:
                del schema[k]


@colander.deferred
def available_languages(node, kw):
    request = kw['request']
    langs = list(request.root.site_settings.get('languages', ()))
    if request.localizer.locale_name not in langs:
        langs.insert(0, request.localizer.locale_name)
    values = [(x, x) for x in langs]
    values.insert(0, ('', _("Any language")))
    return deform.widget.SelectWidget(values=values)


@colander.deferred
def default_language(node, kw):
    request = kw['request']
    return request.localizer.locale_name


class TOSSchema(colander.Schema):
    title = colander.SchemaNode(
        colander.String(),
        title=_("Title"),
    )
    body = colander.SchemaNode(
        colander.String(),
        title=_("Text to agree to"),
        widget=deform.widget.RichTextWidget(),
    )
    revoke_body = colander.SchemaNode(
        colander.String(),
        title=_("Consequences of revoking the agreement"),
        description=_("revoke_body_description",
                      default="Will be displayed when the revocation for "
                              "is shown to inform of the consequences."
                              "If the conseqences are severe, please do express that here!"),
        widget=deform.widget.RichTextWidget(),
    )
    date = colander.SchemaNode(
        colander.Date(),
        title=_("Required from this date"),
        default=default_now,
    )
    lang = colander.SchemaNode(
        colander.String(),
        title=_("Only for this language"),
        description=_("If set, only show this agreement for users using this lang."),
        widget=available_languages,
        default="",
        missing="",
    )
    check_password_on_revoke = colander.SchemaNode(
        colander.Bool(),
        title = _("Require password check on revoke"),
        description=_("This will only be enforced for enabled TOS"),
        default=False
    )
    check_typed_on_revoke = colander.SchemaNode(
        colander.Bool(),
        title = _("Require typing 'I understand' or similar on revoke"),
        description=_("This will only be enforced for enabled TOS"),
        default=False,
    )


def includeme(config):
    config.add_schema('TOS', TOSAgreeSchema, 'agree')
    config.add_schema('TOS', TOSRevokeSchema, 'revoke')
    config.add_schema('TOS', TOSSchema, ['add', 'edit'])
