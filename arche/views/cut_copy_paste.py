from __future__ import unicode_literals
from copy import deepcopy
from uuid import uuid4

from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound
from pyramid.traversal import resource_path
import colander

from arche import _
from arche import security
from arche.utils import generate_slug
from arche.utils import get_addable_content
from arche.views.base import BaseView, BaseForm
from arche.validators import unique_parent_context_name_validator


#FIXME: Check cut, copy and paste functionality.

def can_paste(context, request, view):
    paste_data = request.session.get('__paste_data__')
    if not paste_data:
        return False
    if context.uid == paste_data['uid']:
        return False
    if paste_data['move'] == True:
        path = resource_path(context)
        if view.catalog_search(path = path, uid = paste_data['uid']):
            return False
    cut_obj = view.resolve_uid(paste_data['uid'])
    if not cut_obj:
        return False
    addable = get_addable_content(request.registry).get(cut_obj.type_name, ())
    if context.type_name not in addable:
        return False
    return request.has_permission(cut_obj.add_permission, context)


class CutContext(BaseView):

    def __call__(self):
        self.flash_messages.add(_("Cut"))
        self.request.session['__paste_data__'] = {'uid': self.context.uid, 'move': True}
        return HTTPFound(location = self.request.resource_url(self.context))


class CopyContext(BaseView):

    def __call__(self):
        if len(self.context):
            raise HTTPForbidden("Can't copy objects with subobjects")
        self.flash_messages.add(_("Copy"))
        self.request.session['__paste_data__'] = {'uid': self.context.uid, 'move': False}
        return HTTPFound(location = self.request.resource_url(self.context))


class PasteContext(BaseView):

    def __call__(self):
        if not can_paste(self.context, self.request, self):
            raise HTTPForbidden(_("Can't paste to this context"))
        paste_data = self.request.session.get('__paste_data__')
        cut_obj = self.resolve_uid(paste_data['uid'])
        parent = cut_obj.__parent__
        use_name = generate_slug(self.context, cut_obj.__name__)
        if paste_data.get('move', False):
            del parent[cut_obj.__name__]
            self.flash_messages.add(_("Moved here"))
        else:
            cut_obj.uid = unicode(uuid4())
            cut_obj = deepcopy(cut_obj)
            self.flash_messages.add(_("New copy added here"))
        self.context[use_name] = cut_obj
        del self.request.session['__paste_data__']
        return HTTPFound(location = self.request.resource_url(self.context[use_name]))


class RenameContext(BaseForm):

    def get_schema(self):
        class _RenameSchema(colander.Schema):
            name = colander.SchemaNode(colander.String(),
                                       title = _("Name, this will be part of the url"),
                                       default = self.context.__name__,
                                       validator = unique_parent_context_name_validator,)
        return _RenameSchema()

    @property
    def title(self):
        return _("Rename '${name}'", mapping = {'name': self.context.__name__})

    def save_success(self, appstruct):
        self.flash_messages.add(self.default_success, type="success")
        name = appstruct['name']
        parent = self.context.__parent__
        del parent[self.context.__name__]
        parent[name] = self.context
        return HTTPFound(location = self.request.resource_url(self.context))


def includeme(config):
    config.add_view(CutContext,
                    name = '__cut_context__',
                    permission = security.PERM_DELETE,
                    context = 'arche.interfaces.IContent')
    config.add_view(CopyContext,
                    permission = security.PERM_VIEW,
                    name = '__copy_context__',
                    context = 'arche.interfaces.IContent')
    config.add_view(PasteContext,
                    name = '__paste_context__',
                    context = 'arche.interfaces.IContent')
    config.add_view(RenameContext,
                    renderer = 'arche:templates/form.pt',
                    name = '__rename_context__',
                    permission = security.PERM_MANAGE_SYSTEM,
                    context = 'arche.interfaces.IContent')
