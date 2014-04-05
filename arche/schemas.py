import colander
import deform


class BaseSchema(colander.Schema):
    title = colander.SchemaNode(colander.String())


def includeme(config):
    config.add_content_schema('Document', BaseSchema, 'edit')
    config.add_content_schema('Document', BaseSchema, 'add')
