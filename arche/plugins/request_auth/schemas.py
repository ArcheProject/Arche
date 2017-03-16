import colander


class RequestAuthSchema(colander.Schema):
    userid = colander.SchemaNode(colander.String(),)
    client_ip = colander.SchemaNode(colander.String(),)
    login_max_valid = colander.SchemaNode(colander.Int(),
                                          missing = 30)
    link_valid = colander.SchemaNode(colander.Int(),
                                     missing = 20)
    redirect_url = colander.SchemaNode(colander.String(),
                                       missing = '',
                                        #FIXME: Should validate that it starts with the same domain name instead
                                       validator = colander.url)


def includeme(config):
    config.add_content_schema('Auth', RequestAuthSchema, 'request_session')
