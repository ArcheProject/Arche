from pyramid.config import Configurator
from pyramid.i18n import TranslationStringFactory
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid_zodbconn import get_connection

_ = TranslationStringFactory('Arche')


default_settings = {
    'arche.content_factories': {},
    'arche.content_schemas': {},
}

def includeme(config):
    settings = config.registry.settings
    for key, value in default_settings.items():
        settings.setdefault(key, value)
    config.include('arche.utils')
    config.include('arche.resources')
    config.include('arche.schemas')
    config.include('arche.views')
    from deform_autoneed import resource_registry
    from js.bootstrap import bootstrap_theme
    bootstrap_css_path = 'deform:static/css/bootstrap.min.css'
    assert resource_registry.find_resource(bootstrap_css_path)
    resource_registry.replace_resource(bootstrap_css_path, bootstrap_theme)
    from js.bootstrap import bootstrap_js
    bootstrap_js_path = 'deform:static/scripts/bootstrap.min.js'
    assert resource_registry.find_resource(bootstrap_js_path)
    resource_registry.replace_resource(bootstrap_js_path, bootstrap_js)

def root_factory(request):
    conn = get_connection(request)
    return appmaker(conn.root())

def base_config(**settings):
    from .security import groupfinder
    authn_policy = AuthTktAuthenticationPolicy(secret = read_salt(settings),
                                               callback = groupfinder,
                                               hashalg = 'sha512')
    authz_policy = ACLAuthorizationPolicy()
    return Configurator(root_factory = root_factory,
                        settings = settings,
                        authentication_policy=authn_policy,
                        authorization_policy=authz_policy,)
    

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = base_config(**settings)
    config.include('arche')
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.include('pyramid_beaker')
    config.include('pyramid_zodbconn')
    config.include('pyramid_tm')
    config.include('pyramid_deform')
    config.include('pyramid_chameleon')
    config.include('deform_autoneed')
    #config.add_translation_dirs('arche:locale/')
    return config.make_wsgi_app()

def appmaker(zodb_root):
    try:
        #FIXME: This is a good injection point for a bootstrap-view of some kind
        return zodb_root['app_root']
    except KeyError:
        zodb_root['app_root'] = populate_database()
        import transaction
        transaction.commit()
        return zodb_root['app_root']

def populate_database():
    from .resources import Document
    return Document()

def read_salt(settings):
    from uuid import uuid4
    from os.path import isfile
    filename = settings.get('salt_file', None)
    if filename is None:
        print "\nUsing random salt which means that all users must reauthenticate on restart."
        print "Please specify a salt file by adding the parameter:\n"
        print "salt_file = <path to file>\n"
        print "in paster ini config and add the salt as the sole contents of the file.\n"
        return str(uuid4())
    if not isfile(filename):
        print "\nCan't find salt file specified in paster ini. Trying to create one..."
        f = open(filename, 'w')
        salt = str(uuid4())
        f.write(salt)
        f.close()
        print "Wrote new salt in: %s" % filename
        return salt
    else:
        f = open(filename, 'r')
        salt = f.read()
        if not salt:
            raise ValueError("Salt file is empty - it needs to contain at least some text. File: %s" % filename)
        f.close()
        return salt
