from logging import getLogger

from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.config import Configurator
from pyramid.i18n import TranslationStringFactory
from pyramid_zodbconn import get_connection
from six import string_types

_ = TranslationStringFactory('Arche')
logger = getLogger(__name__)


default_settings = {
    'arche.hash_method': 'arche.security.sha512_hash_method',
    'arche.includes': '',
#   'arche.favicon': 'arche:static/favicon.ico',
    'arche.debug': False,
    'arche.use_exception_views': True,
    'arche.timezone': 'UTC', #Default timezone
    'arche.cache_max_age': 24*60*60, #seconds
    'arche.new_userid_validator': 'arche.validators.NewUserIDValidator',
    'arche.actionbar': 'arche.views.actions.render_actionbar',
    #Set template dir for deform overrides
    'pyramid_deform.template_search_path': 'arche:templates/deform/',
}


def includeme(config):
    settings = config.registry.settings
    for key, value in default_settings.items():
        settings.setdefault(key, value)
    adjust_bools(settings)

    config.include('arche.utils')
    config.include('arche.subscribers')
    config.include('arche.resources')
    config.include('arche.security')
    config.include('arche.models')
    config.include('arche.schemas')
    config.include('arche.views')
    config.include('arche.portlets')
    config.include('arche.populators')
    #Portlets
    config.include('arche.portlets.byline')
    config.include('arche.portlets.navigation')
    #Translations
    config.add_translation_dirs('arche:locale/')
    #Turn these strings into methods
    resolvable_methods = ('arche.hash_method',
                          'arche.new_userid_validator',
                          'arche.actionbar',)
    for name in resolvable_methods:
        if isinstance(settings[name], string_types):
            settings[name] = config.name_resolver.resolve(settings[name])

    #Inject dependencies in deform
    config.include('.fanstatic_lib')

    #Include other arche plugins
    for package in config.registry.settings.get('arche.includes', '').strip().splitlines():
        config.include(package)

    #setup workflows
    config.include('arche.models.workflow.read_paster_wf_config')


def root_factory(request):
    conn = get_connection(request)
    return appmaker(conn.root())

def base_config(**settings):
    from arche.security import groupfinder
    authn_policy = AuthTktAuthenticationPolicy(secret = read_salt(settings),
                                               callback = groupfinder,
                                               hashalg = 'sha512')
    authz_policy = ACLAuthorizationPolicy()
    return Configurator(root_factory = root_factory,
                        settings = settings,
                        authentication_policy = authn_policy,
                        authorization_policy = authz_policy,)

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = base_config(**settings)
    cache_max_age = int(settings.get('arche.cache_max_age', 60*60*24))
    config.add_static_view('static', 'arche:static', cache_max_age = cache_max_age)
    config.include('arche') #Must be included first to adjust settings for other packages!
    config.include('pyramid_beaker')
    config.include('pyramid_zodbconn')
    config.include('pyramid_tm')
    config.include('pyramid_deform')
    config.include('pyramid_chameleon')
    config.include('deform_autoneed')
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
            #Attach and remove setup context
            zodb_root['app_root'] = root_populator(**data)
            del zodb_root['initial_setup']
            return zodb_root['app_root']

def adjust_bools(settings):
    true_vals = set(['true', '1', 'on'])
    false_vals = set(['false', '0', 'off'])
    for (k, v) in settings.copy().items():
        if not k.startswith('arche.') or not isinstance(v, basestring):
            continue
        if v.lower() in true_vals:
            settings[k] = True
        elif v.lower() in false_vals:
            settings[k] = False

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
