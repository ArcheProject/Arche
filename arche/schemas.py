import colander
import deform

from arche.validators import unique_context_name_validator
from arche import _


class BaseSchema(colander.Schema):
    title = colander.SchemaNode(colander.String())
    description = colander.SchemaNode(colander.String(),
                                      widget = deform.widget.TextAreaWidget(rows = 5),
                                      missing = u"")


class UserSchema(colander.Schema):
    first_name = colander.SchemaNode(colander.String())
    last_name = colander.SchemaNode(colander.String())


class AddUserSchema(UserSchema):
    userid = colander.SchemaNode(colander.String(),
                                 validator = unique_context_name_validator)


class InitialSetup(colander.Schema):
    title = colander.SchemaNode(colander.String(),
                                title = _(u"Site title"))
    userid = colander.SchemaNode(colander.String(),
                                 title = _(u"Admin userid"))
    email = colander.SchemaNode(colander.String(),
                                title = _(u"Admins email adress"),
                                validator = colander.Email())
    password = colander.SchemaNode(colander.String(),
                                   title = _(u"Admins password"),
                                   widget = deform.widget.CheckedPasswordWidget())


def includeme(config):
    config.add_content_schema('Document', BaseSchema, 'view')
    config.add_content_schema('Document', BaseSchema, 'edit')
    config.add_content_schema('Document', BaseSchema, 'add')
    config.add_content_schema('User', UserSchema, 'view')
    config.add_content_schema('User', UserSchema, 'edit')
    config.add_content_schema('User', AddUserSchema, 'add')
    config.add_content_schema('InitialSetup', InitialSetup, 'setup')
