from pyramid.config import Configurator
from pyramid.i18n import TranslationStringFactory
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid_zodbconn import get_connection

_ = TranslationStringFactory('Arche')


default_settings = {
    'arche.hash_method': 'arche.utils.default_hash_method',
    #Set template dir for deform overrides
    'pyramid_deform.template_search_path': 'arche:templates/deform/',
}

def includeme(config):
    settings = config.registry.settings
    for key, value in default_settings.items():
        settings.setdefault(key, value)
    config.include('arche.utils')
    config.include('arche.resources')
    config.include('arche.schemas')
    config.include('arche.views')
    config.include('arche.security')
    config.include('arche.catalog')
    config.include('arche.portlets')
    #Resolve strings
    if isinstance(settings['arche.hash_method'], str):
        settings['arche.hash_method'] = config.name_resolver.resolve(settings['arche.hash_method'])
    from deform_autoneed import resource_registry
    #Replace bootstrap theme
    from js.bootstrap import bootstrap_theme
    bootstrap_css_path = 'deform:static/css/bootstrap.min.css'
    #import pdb;pdb.set_trace()
    assert resource_registry.find_resource(bootstrap_css_path)
    resource_registry.replace_resource(bootstrap_css_path, bootstrap_theme)
    #Replace jquery
    from js.jquery import jquery
    jquery_path = 'deform:static/scripts/jquery-2.0.3.min.js'
    assert resource_registry.find_resource(jquery_path)
    resource_registry.replace_resource(jquery_path, jquery)
    #Replace bootstrap
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

def override_perm_methods(config):
    """ Important override, see has_permission. """
    from arche.security import has_permission
    config.add_request_method(has_permission, name = 'has_permission')

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = base_config(**settings)
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.include('arche') #Must be included first to adjust settings for other packages!
    config.include(override_perm_methods)
    config.include('pyramid_beaker')
    config.include('pyramid_zodbconn')
    config.include('pyramid_tm')
    config.include('pyramid_deform')
    config.include('pyramid_chameleon')
    config.include('deform_autoneed')
    #config.add_translation_dirs('arche:locale/')
    config.hook_zca()
    return config.make_wsgi_app()

def appmaker(zodb_root):
    try:
        return zodb_root['app_root']
    except KeyError:
        from pyramid.threadlocal import get_current_registry
        from zope.interface import alsoProvides
        import transaction

        from arche.utils import get_content_factories
        from arche.interfaces import IRoot
        from arche.populators import root_populator

        factories = get_content_factories()
        #This is where initial population takes place, but first some site setup
        if not 'initial_setup' in zodb_root or not zodb_root['initial_setup'].setup_data:
            InitialSetup = factories['InitialSetup']
            zodb_root['initial_setup'] = InitialSetup()
            transaction.commit()
            return zodb_root['initial_setup']
        else:
            #FIXME move this population to its own method so tests can use it
            #Root added
            data = dict(zodb_root['initial_setup'].setup_data)
            root = root_populator(**data)
            #Attach and remove setup context
            zodb_root['app_root'] = root
            del zodb_root['initial_setup']
            return zodb_root['app_root']

def read_salt(settings):
    from uuid import uuid4
    from os.path import isfile
    filename = settings.get('arche.salt_file', None)
    if filename is None:
        print "\nUsing random salt which means that all users must reauthenticate on restart."
        print "Please specify a salt file by adding the parameter:\n"
        print "arche.salt_file = <path to file>\n"
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
