# -*- coding: utf-8 -*-
from fanstatic.config import convert_config
from fanstatic.publisher import Publisher
import fanstatic
import wsgiref.util
from pyramid.settings import asbool


def fanstatic_config(config, prefix='fanstatic.'):
    cfg = {
        'publisher_signature': fanstatic.DEFAULT_SIGNATURE,
        'injector': 'topbottom',
    }
    for k, v in config.items():
        if k.startswith(prefix):
            cfg[k[len(prefix):]] = v
    return convert_config(cfg)


class FanstaticTween(object):
    def __init__(self, handler, config):
        self.use_application_uri = asbool(
            config.pop('fanstatic.use_application_uri', False))
        self.config = fanstatic_config(config)
        self.handler = handler
        self.publisher = Publisher(fanstatic.get_library_registry())
        self.publisher_signature = self.config.get('publisher_signature')
        self.trigger = '/%s/' % self.publisher_signature
        injector_name = self.config.pop('injector')
        self.injector = None
        registry = fanstatic.registry
        if hasattr(registry, 'InjectorRegistry'):
            injector_factory = registry.InjectorRegistry.instance().get(
                injector_name)
            self.injector = injector_factory(self.config)

    def __call__(self, request):

        # publisher
        if len(request.path_info.split(self.trigger)) > 1:
            path_info = request.path_info
            ignored = request.path_info_pop()
            while ignored != self.publisher_signature:
                ignored = request.path_info_pop()
            response = request.get_response(self.publisher)
            # forward to handler if the resource could not be found
            if response.status_int == 404:
                request.path_info = path_info
                return self.handler(request)
            return response

        # injector
        needed = fanstatic.init_needed(**self.config)
        if self.use_application_uri and not needed.has_base_url():
            base_url = wsgiref.util.application_uri(request.environ)
            # remove trailing slash for fanstatic
            needed.set_base_url(base_url.rstrip('/'))
        request.environ[fanstatic.NEEDED] = needed

        response = self.handler(request)

        if not (response.content_type and
                response.content_type.lower() in ['text/html',
                                                  'text/xml']):
            fanstatic.del_needed()
            return response

        if needed.has_resources():
            if self.injector is not None:
                result = self.injector(response.body,
                                       needed, request, response)
            else:
                result = needed.render_topbottom_into_html(response.body)
            try:
                response.text = ''
            except TypeError:
                response.body = ''
            response.write(result)
        fanstatic.del_needed()
        return response


def static_tween_factory(handler, registry):
    return FanstaticTween(handler, registry.settings.copy())


def includeme(config):
    config.add_tween('.static_resources.static_tween_factory')
