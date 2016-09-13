import colander

from arche import _
from arche.interfaces import ISchemaCreatedEvent
from arche.schemas import LoginSchema


@colander.deferred
def _deferred_default_session_max_valid(node, kw):
    request = kw['request']
    return request.registry.settings.get('arche.auth.default_max_valid', 60)


class AuthSessionSchema(colander.Schema):
    title = colander.SchemaNode(
        colander.String(),
        title = _("Human-readable name of session"),
        description = _("Good as a reminder if you use this session for api access."),
        missing = ""
    )
    max_valid = colander.SchemaNode(
        colander.Int(),
        title = _("Session will timeout after this time (in minutes) has expired."),
        description = _("If emtpy, this session will never expire. "
                        "Recommended for key-based authentication."),
        default = _deferred_default_session_max_valid,
        missing = None,
    )
    api_key = colander.SchemaNode(
        colander.String(),
        title = _("Allow authentication with this key"),
        missing = "",
        #validator = colander.Length(min = 20) <- Maybe later?
    )
    ip_locked = colander.SchemaNode(
        colander.Sequence(),
        colander.SchemaNode(colander.String(),
                            title = _("IP"),
                            name='foo'),
        title = _("Limit access to these IP-addresses"),
    )


#FIXME: Figure out a way to inject this in the login schema, or
#create a message after login about timeout
def update_login_schema(schema, event):
    schema.add_node(
        colander.SchemaNode(
            colander.Bool(),
            name = "keep_me_logged_in",
            title = _("Keep me logged in"),
            description = _("keep_me_logged_in_description",
                            default = "Your session will never time out. "
                                      "Don't use this on a public computer!")))

def includeme(config):
    config.add_content_schema('Auth', AuthSessionSchema, ('add', 'edit'))
#    config.add_subscriber(update_login_schema, [LoginSchema, ISchemaCreatedEvent])
