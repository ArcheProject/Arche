from logging import getLogger

from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.config import Configurator
from pyramid.i18n import TranslationStringFactory
from pyramid.util import DottedNameResolver
from pyramid_zodbconn import get_connection
from six import string_types

_ = TranslationStringFactory('Arche')
logger = getLogger(__name__)


default_settings = {
    'arche.hash_method': 'arche.security.sha512_hash_method',
    'arche.session_factory': 'pyramid_beaker',
    'arche.includes': '',
    'arche.debug': False,
    'arche.use_exception_views': True,
    'arche.timezone': 'UTC', #Default timezone
    'arche.cache_max_age': 24*60*60, #seconds
    'arche.new_userid_validator': 'arche.validators.NewUserIDValidator',
    'arche.actionbar': 'arche.views.actions.render_actionbar',
    'arche.auto_recreate_catalog': False,
    'arche.favicon': '',
    #Set template dir for deform overrides
    'pyramid_deform.template_search_path': 'arche:templates/deform/',
    'arche.authn_factory': 'arche.security.auth_tkt_factory',
    'arche.auth.max_sessions': 5, #Per user
    'arche.auth.activity_update': 60, #Seconds
    'arche.auth.default_max_valid': 60, #Minutes
    'arche.auth.max_keep_days': 30, #Days since last activity
}

def setup_defaults(settings):
    """ Make sure default settings exist. This will fire twice during normal startup since some settings
        are required early. Make sure it doesn't destroy any existing settings!
    """
    for key, value in default_settings.items():
        settings.setdefault(key, value)
    adjust_bools(settings)
    ints = ['arche.auth.max_sessions',
            'arche.auth.activity_update',
            'arche.auth.default_max_valid',
            'arche.auth.max_keep_days']
    adjust_ints(settings, ints)

def includeme(config):
    setup_defaults(config.registry.settings) #This will run twice...
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
    config.include('arche.portlets.contents')
    config.include('arche.portlets.richtext')
    #Translations
    config.add_translation_dirs('arche:locale/')

    #Inject dependencies in deform
    config.include('.fanstatic_lib')

    #Include other arche plugins
    for package in config.registry.settings.get('arche.includes', '').strip().splitlines():
        config.include(package)

    #Turn these strings into methods
    resolvable_methods = ('arche.hash_method',
                          'arche.new_userid_validator',
                          'arche.actionbar',)
    settings = config.registry.settings
    for name in resolvable_methods:
        if isinstance(settings[name], string_types):
            settings[name] = config.name_resolver.resolve(settings[name])

    #setup workflows
    config.include('arche.models.workflow.read_paster_wf_config')

    #setup versioning from paster config
    config.include('arche.models.versioning.read_paster_versioning_config')

    #Include session factory
    config.include(settings['arche.session_factory'].strip())


def root_factory(request):
    conn = get_connection(request)
    return appmaker(conn.root())

def base_config(**settings):
    resolver = DottedNameResolver()
    setup_defaults(settings)
    authn_policy = resolver.maybe_resolve(settings['arche.authn_factory'])(settings)
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
    config.include('betahaus.viewcomponent')
    config.include('pyramid_deform')
    config.include('deform_autoneed')
    config.include('arche') #Must be included first to adjust settings for other packages!
    config.include('pyramid_zodbconn')
    config.include('pyramid_tm')
    config.include('pyramid_chameleon')
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
        from arche.models.evolver import run_initial_migrations

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
            zodb_root['app_root'] = root = root_populator(**data)
            transaction.commit()
            run_initial_migrations(root)
            del zodb_root['initial_setup']
            return root

def adjust_bools(settings):
    true_vals = set(['true', 'on'])
    false_vals = set(['false', 'off'])
    for (k, v) in settings.copy().items():
        if not k.startswith('arche.') or not isinstance(v, string_types):
            continue
        if v.lower() in true_vals:
            settings[k] = True
        elif v.lower() in false_vals:
            settings[k] = False

def adjust_ints(settings, keys):
    for k in keys:
        settings[k] = int(settings[k])
