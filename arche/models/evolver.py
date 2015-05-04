from __future__ import unicode_literals

from pyramid.interfaces import IApplicationCreated
from pyramid.threadlocal import get_current_registry
from repoze.evolution import ZODBEvolutionManager
from repoze.evolution import evolve_to_latest
from zope.component import adapter
from zope.interface import implementer

from arche import logger
from arche.evolve import VERSION
from arche.exceptions import EvolverVersionError
from arche.interfaces import IEvolver
from arche.interfaces import IRoot


@adapter(IRoot)
@implementer(IEvolver)
class BaseEvolver(object):
    name = ""
    sw_version = 0
    version_requirements = {}

    def __init__(self, context):
        self.context = context

    @property
    def evolve_packagename(self):
        return "%s.evolve" % self.name

    @property
    def db_version(self):
        manager = self.get_manager()
        return manager.get_db_version()

    @property
    def needs_upgrade(self):
        return self.db_version != self.sw_version

    def get_manager(self):
        return ZODBEvolutionManager(self.context,
                                    evolve_packagename = self.evolve_packagename,
                                    sw_version = self.sw_version,
                                    initial_db_version = self.sw_version)

    def evolve(self):
        if self.needs_upgrade:
            logger.info("Running evolve with package '%s'. Current version: %s - target version: %s",
                        self.name, self.db_version, self.sw_version)
            missing = self.check_requirements()
            if missing:
                msg = "Version requirements not met. The following are required:\n"
                for (name, ver) in missing.items():
                    msg += "%s: %s\n" % (name, ver)
                raise EvolverVersionError(msg)
            manager = self.get_manager()
            evolve_to_latest(manager)
        else:
            logger.debug("'%s' is already up to date.", self.name)

    def check_requirements(self):
        reg = get_current_registry()
        found_missing = {}
        for (name, version_num) in self.version_requirements.items():
            #Explain a missing adapter better?
            evolver = reg.getAdapter(self.context, IEvolver, name = name)
            if evolver.db_version < version_num:
                found_missing[name] = evolver.db_version
        return found_missing


class ArcheEvolver(BaseEvolver):
    name = 'arche'
    sw_version = VERSION


def check_sw_versions(event = None, env = None):
    """ Make sure software and database versions are up to date.
    """
    #This should be changed into something more sensible.
    #Env vars?
    from sys import argv
    script_names = ['bin/arche', 'bin/evolver', 'bin/pshell']
    if argv[0] in script_names:
        return
    if env is None:
        from pyramid.scripting import prepare
        env = prepare()
    root = env['root']
    if not IRoot.providedBy(root):
        logger.info("Root object is %r, so check_sw_versions won't run", root)
        return
    registry = env['registry']
    names = set()
    for ar in registry.registeredAdapters():
        if ar.provided == IEvolver:
            names.add(ar.name)
    needed = set()
    for name in names:
        evolver = registry.getAdapter(root, IEvolver, name = name)
        logger.debug("Evolver '%s': DB ver: %s Software version: %s",
                     name, evolver.db_version, evolver.sw_version)
        if evolver.needs_upgrade:
            needed.add(evolver.name)
    if needed:
        msg = "The following packages aren't up to date: '%s'\n" % "', '".join(needed)
        msg += "Run 'bin/evolver <your paster ini> <package name>' to upgrade"
        raise EvolverVersionError(msg)
    env['closer']()

def add_evolver(config, evolver):
    config.registry.registerAdapter(evolver, name = evolver.name)

def includeme(config):
    config.add_directive('add_evolver', add_evolver)
    config.add_evolver(ArcheEvolver)
    config.add_subscriber(check_sw_versions, IApplicationCreated)
