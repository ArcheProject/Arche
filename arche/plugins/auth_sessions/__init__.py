

def includeme(config):
    if config.registry.settings['arche.authn_factory'] != 'arche.plugins.auth_sessions.authn_factory':
        from pyramid.exceptions import ConfigurationError
        raise ConfigurationError("""
        When this package is included, the value 'arche.authn_factory' must be set to
        'arche.plugins.auth_sessions.authn_factory'.

        The ViewDerrivers in Pyramid caches the authentication method on registry,
        so as soon as views have been registered it's no longer
        possible to change authentication policy.""")
    config.include('.models')
    config.include('.schemas')
    config.include('.views')

def authn_factory(settings):
    from .models import ExtendedSessionAuthenticationPolicy
    from arche.security import groupfinder
    return ExtendedSessionAuthenticationPolicy(callback=groupfinder)
