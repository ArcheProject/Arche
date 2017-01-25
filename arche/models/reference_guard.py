from itertools import islice

from pyramid.interfaces import IRequest
from pyramid.threadlocal import get_current_request
from six import string_types
from zope.component import adapter
from zope.interface.declarations import implementer

from arche import _
from arche import logger
from arche.compat import IterableUserDict
from arche.exceptions import ReferenceGuarded
from arche.interfaces import IBase
from arche.interfaces import IReferenceGuards
from arche.interfaces import IObjectWillBeRemovedEvent
from arche.security import PERM_VIEW


@adapter(IRequest)
@implementer(IReferenceGuards)
class ReferenceGuards(object):

    def __init__(self, request):
        self.request = request
        self._gregistry = request.registry._ref_guards
        self._moving_uids = set()

    def get_valid(self, context):
        for ref_guard in self._gregistry.values():
            if ref_guard.valid_context(context):
                yield ref_guard

    def check(self, context):
        context_will_move = context.uid in self._moving_uids
        for ref_guard in self.get_valid(context):
            if context_will_move and ref_guard.allow_move:
                continue
            ref_guard(self.request, context)

    def get_vetoing(self, context):
        context_will_move = context.uid in self._moving_uids
        for ref_guard in self.get_valid(context):
            if context_will_move and ref_guard.allow_move:
                continue
            if ref_guard.get_guarded_count(self.request, context):
                yield ref_guard

    def moving(self, uid):
        """ Prepare to allow move of context with this uid. """
        assert isinstance(uid, string_types)
        self._moving_uids.add(uid)


class RefGuard(object):
    callable = None
    name = ''
    title = ''
    requires = None
    catalog_result = False
    allow_move = True

    def __init__(self, _callable,
                 name=None,
                 requires=(IBase,),
                 title=None,
                 catalog_result=False,
                 allow_move=True):
        self.callable = _callable
        if name is None:
            self.name = _callable.__name__
        if title is None:
            title = _("Reference guard named: ${name}",
                      mapping={'name': self.name})
        self.title = title
        self.requires = requires
        self.catalog_result = catalog_result
        self.allow_move = allow_move

    def __call__(self, request, context):
        if self.valid_context(context):
            if self.catalog_result:
                guarded = self.callable(request, context)[1]
            else:
                guarded = self.callable(request, context)
            if guarded:
                raise ReferenceGuarded(context, self, guarded=guarded)

    def valid_context(self, context):
        for iface in self.requires:
            if iface.providedBy(context):
                return True
        return False

    def get_guarded_count(self, request, context):
        """ This should always be the exact count, regardless of permissions. """
        if self.valid_context(context):
            if self.catalog_result:
                return self.callable(request, context)[0].total
            else:
                return len(self.callable(request, context))

    def get_guarded_objects(self, request, context, perm=PERM_VIEW, limit=5):
        """ Returns iterator with """
        if self.valid_context(context):
            if self.catalog_result:
                result = request.resolve_docids(self.callable(request, context)[1], perm=perm)
            else:
                result = _generator_with_guard(self.callable, request, context, perm=perm)
            if limit:
                return islice(result, limit)
            return result
        return iter([])


class _ReferenceGuardsRegistry(IterableUserDict):

    def add(self, ref_guard):
        assert isinstance(ref_guard, RefGuard)
        if ref_guard.name in self:
            logger.warn('Replacing reference guard %r', ref_guard.name)
        self[ref_guard.name] = ref_guard


def _generator_with_guard(callable, request, context, perm=PERM_VIEW):
    for obj in callable(request, context):
        if request.has_permission(perm, obj):
            yield obj


def add_ref_guard(config, _callable,
                  name=None,
                  requires=(IBase,),
                  catalog_result=False,
                  title=None,
                  allow_move=True):
    ref_guard = RefGuard(
        _callable,
        name=name,
        requires=tuple(requires),
        catalog_result=catalog_result,
        title=title,
        allow_move=allow_move,
    )
    guards_reg = config.registry._ref_guards
    # FIXME: Implement pyramids config commit structure with conflict checks?
    guards_reg.add(ref_guard)


def reference_guards(request):
    return IReferenceGuards(request)


def _protect_guarded_from_delete(context, event):
    request = getattr(event, 'request', get_current_request())
    request.reference_guards.check(context)


def includeme(config):
    config.registry._ref_guards = _ReferenceGuardsRegistry()
    config.registry.registerAdapter(ReferenceGuards)
    config.add_directive('add_ref_guard', add_ref_guard)
    config.add_request_method(reference_guards, reify=True)
    config.add_subscriber(_protect_guarded_from_delete, [IBase, IObjectWillBeRemovedEvent])
