from pyramid import events

@events.subscriber(events.NewResponse)
def add_xua_header(event):
  """Adds the X-UA-Compatible header for HTML responses to IE."""
  if ('MSIE' in (event.request.user_agent or '') and
      'html' in (event.response.content_type or '')):
    event.response.headers['X-UA-Compatible'] = 'IE=edge,chrome=1'

def includeme(config):
    config.scan('arche.views.ie_compat_header')