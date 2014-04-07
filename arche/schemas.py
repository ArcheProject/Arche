import colander
import deform

from arche.validators import unique_context_name_validator

class BaseSchema(colander.Schema):
    title = colander.SchemaNode(colander.String())


class UserSchema(colander.Schema):
    first_name = colander.SchemaNode(colander.String())
    last_name = colander.SchemaNode(colander.String())


class AddUserSchema(UserSchema):
    userid = colander.SchemaNode(colander.String(),
                                 validator = unique_context_name_validator)

def includeme(config):
    config.add_content_schema('Document', BaseSchema, 'edit')
    config.add_content_schema('Document', BaseSchema, 'add')
    config.add_content_schema('User', UserSchema, 'edit')
    config.add_content_schema('User', AddUserSchema, 'add')
    