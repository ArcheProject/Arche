import colander
import deform

from arche.validators import unique_context_name_validator
from arche.validators import login_password_validator
from arche.validators import unique_userid_validator
from arche import _


tabs = {'': _(u"Default"),
        'visibility': _(u"Visibility"),
        'metadata': _(u"Metadata")}


@colander.deferred
def current_userid(node, kw):
    userid = kw['request'].userid
    return userid and userid or colander.null


class DCMetadataSchema(colander.Schema):
    title = colander.SchemaNode(colander.String())
    description = colander.SchemaNode(colander.String(),
                                      widget = deform.widget.TextAreaWidget(rows = 5),
                                      missing = u"")
    creator = colander.SchemaNode(colander.String(),
                                  tab = 'metadata',
                                  missing = colander.null,
                                  default = current_userid)
    contributor = colander.SchemaNode(colander.String(),
                                      tab = 'metadata',
                                      missing = colander.null)
    created = colander.SchemaNode(colander.DateTime(),
                                  missing = colander.null,
                                  tab = 'metadata')
    modified = colander.SchemaNode(colander.DateTime(),
                                   missing = colander.null,
                                   tab = 'metadata')
    publisher = colander.SchemaNode(colander.String(),
                                    missing = colander.null,
                                  tab = 'metadata')
    date = colander.SchemaNode(colander.DateTime(),
                               missing = colander.null,
                                  tab = 'metadata')
    subject = colander.SchemaNode(colander.String(),
                                   title = _(u"Tags or subjects"),
                                missing = colander.null,
                                  tab = 'metadata')
    relation = colander.SchemaNode(colander.String(),
                                   title = _(u"Links or relations to other content"),
                                   missing = colander.null,
                                  tab = 'metadata')
    rights = colander.SchemaNode(colander.String(),
                                 title = _(u"Licensing"),
                                 missing = colander.null,
                                 tab = 'metadata')
    #type?
    #format
    #identifier -> url
    #source
    #language
    #relation?


class BaseSchema(DCMetadataSchema):
    nav_visible = colander.SchemaNode(colander.Bool(),
                                      title = _(u"Show in navigations"),
                                      missing = True,
                                      default = True,
                                      tab = tabs['visibility'])
    listing_visible = colander.SchemaNode(colander.Bool(),
                                          title = _(u"Show in listing or table views"),
                                          description = _(u"The content view will always show this regardless of what you set."),
                                          missing = True,
                                          default = True,
                                          tab = tabs['visibility'])


class DocumentSchema(BaseSchema):
    body = colander.SchemaNode(colander.String(),
                               widget = deform.widget.RichTextWidget(),
                               missing = colander.null)


class UserSchema(colander.Schema):
    first_name = colander.SchemaNode(colander.String(),
                                     title = _(u"First name"),
                                     missing = u"")
    last_name = colander.SchemaNode(colander.String(),
                                    title = _(u"Last name"),
                                    missing = u"")
    email = colander.SchemaNode(colander.String(),
                                title = _(u"Email adress"),
                                validator = colander.Email())
    

class AddUserSchema(UserSchema):
    userid = colander.SchemaNode(colander.String(),
                                 validator = unique_context_name_validator)
    password = colander.SchemaNode(colander.String(),
                                   title = _(u"Password"),
                                   widget = deform.widget.CheckedPasswordWidget())


class ChangePasswordSchema(colander.Schema):
    #FIXME: Validate old password
    password = colander.SchemaNode(colander.String(),
                                   title = _(u"Password"),
                                   widget = deform.widget.CheckedPasswordWidget())


class InitialSetup(colander.Schema):
    title = colander.SchemaNode(colander.String(),
                                title = _(u"Site title"))
    userid = colander.SchemaNode(colander.String(),
                                 title = _(u"Admin userid"),
                                 validator = unique_context_name_validator)
    email = colander.SchemaNode(colander.String(),
                                title = _(u"Admins email adress"),
                                validator = colander.Email())
    password = colander.SchemaNode(colander.String(),
                                   title = _(u"Admins password"),
                                   widget = deform.widget.CheckedPasswordWidget())


class LoginSchema(colander.Schema):
    validator = login_password_validator
    email = colander.SchemaNode(colander.String(),
                                 title = _(u"Email"),)
    password = colander.SchemaNode(colander.String(),
                                   title = _(u"Password"),
                                   widget = deform.widget.PasswordWidget())


class RegisterSchema(colander.Schema):
    userid = colander.SchemaNode(colander.String(),
                                 title = _(u"UserID"),
                                 validator = unique_userid_validator)
    email = colander.SchemaNode(colander.String(),
                                title = _(u"Email"),
                                #FIXME: Validate unique email
                                validator = colander.Email())
    password = colander.SchemaNode(colander.String(), #FIXME REMOVE!
                                   title = _(u"Password"),
                                   widget = deform.widget.PasswordWidget())


def includeme(config):
    config.add_content_schema('Document', DocumentSchema, 'view')
    config.add_content_schema('Document', DocumentSchema, 'edit')
    config.add_content_schema('Document', DocumentSchema, 'add')
    config.add_content_schema('User', UserSchema, 'view')
    config.add_content_schema('User', UserSchema, 'edit')
    config.add_content_schema('User', AddUserSchema, 'add')
    config.add_content_schema('User', ChangePasswordSchema, 'change_password')
    config.add_content_schema('InitialSetup', InitialSetup, 'setup')
    config.add_content_schema('Auth', LoginSchema, 'login')
    config.add_content_schema('Auth', RegisterSchema, 'register')
