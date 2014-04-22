import warnings

import colander
import deform
from pyramid.traversal import find_root
from pyramid.traversal import lineage
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPNotFound
from pyramid.decorator import reify
from pyramid.renderers import get_renderer
from pyramid.renderers import render
from pyramid.view import render_view_to_response
from pyramid_deform import FormView
from deform_autoneed import need_lib

from arche.utils import get_flash_messages
from arche.utils import generate_slug
from arche.utils import get_view
from arche.utils import get_content_factories
from arche.utils import get_content_schemas
from arche.utils import get_content_views
from arche.fanstatic_lib import main_css
from arche.portlets import get_portlet_manager
from arche.interfaces import IFolder, IThumbnails
from arche import security
from arche import _


class BaseView(object):
    
    def __init__(self, context, request):
        self.context = context
        self.request = request
        need_lib('basic')
        main_css.need()

    @reify
    def root(self):
        return find_root(self.context)

    @reify
    def flash_messages(self):
        return get_flash_messages(self.request)

    def render_portlet_slot(self, slot, **kw):
        results = []
        context = self.context
        while context:
            manager = get_portlet_manager(context, self.request.registry)
            if manager:
                #Use the view context when calling the portlets!
                results.extend(manager.render_slot(slot, self.context, self.request, self, **kw))
            context = getattr(context, '__parent__', None)
        return results

    def catalog_query(self, **kwargs):
        #FIXME: inject permisison check here or always assume unsafe?
        return self.root.catalog.query(**kwargs)

    def breadcrumbs(self):
        return reversed(list(lineage(self.context)))

    def get_content_factory(self, name):
        return get_content_factories(self.request.registry).get(name)

    def macro(self, asset_spec, macro_name='main'):
        return get_renderer(asset_spec).implementation().macros[macro_name]

    def addable_content(self, context):
        for factory in get_content_factories(self.request.registry).values():
            if getattr(context, 'type_name', None) in getattr(factory, 'addable_to', ()):
                if self.request.has_permission(factory.add_permission, context):
                    yield factory

    def render_template(self, renderer, **kwargs):
        kwargs.setdefault('view', self)
        return render(renderer, kwargs, self.request)

    def render_actionbar(self, context):
        if self.request.authenticated_userid:
            return self.render_template('arche:templates/action_bar.pt')

    def get_local_nav_objects(self, context):
        #FIXME: Conditions for navigation!
        if IFolder.providedBy(context):
            for obj in context.values():
                if getattr(obj, 'nav_visible', False):
                    if self.request.has_permission(security.PERM_VIEW, obj):
                        yield obj

    def selectable_views(self, context):
        type_name = getattr(context,'type_name', None)
        selectable = {'view': _(u"Default")}
        views = get_content_views(self.request.registry)
        selectable.update(views.get(type_name, {}))
        return selectable

    def query_view(self, context, name = '', default = ''):
        result = get_view(context, self.request, view_name = name)
        return result and name or default

    def byte_format(self, num):
        """ Return a tuple with size and unit. """
        for x in ['bytes', 'Kb', 'Mb', 'Gb']:
            if num < 1024.0 and num > -1024.0:
                return (u"%3.1f" % num, x)
            num /= 1024.0
        return (u"%3.1f" % num, 'Tb')

    def thumb_tag(self, context, scale_name, default = u"", extra_cls = '', **kw):
        #FIXME: Default?
        url = self.request.thumb_url(context, scale_name)
        if not url:
            return default
        thumbnails = self.request.registry.queryAdapter(context, IThumbnails)
        if not thumbnails:
            return default
        thumb = thumbnails.get_thumb(scale_name)
        if thumb:
            data = {'src': url,
                    'width': thumb.width,
                    'height': thumb.height,
                    'class': 'thumb-%s img-responsive' % scale_name,
                    'alt': context.title,
                    }
            if extra_cls:
                data['class'] += " %s" % extra_cls
            data.update(kw)
            return u"<img %s />" % " ".join(['%s="%s"' % (k, v) for (k, v) in data.items()])
        return default


class BaseForm(BaseView, FormView):
    default_success = _(u"Done")
    default_cancel = _(u"Canceled")
    schema_name = u''
    type_name = u''
    heading = u''

    button_delete = deform.Button('delete', title = _(u"Delete"), css_class = 'btn btn-danger')
    button_cancel = deform.Button('cancel', title = _(u"Cancel"), css_class = 'btn btn-default')
    button_save = deform.Button('save', title = _(u"Save"), css_class = 'btn btn-primary')
    button_add = deform.Button('add', title = _(u"Add"), css_class = 'btn btn-primary')

    buttons = (button_save, button_cancel,)

    def __call__(self):
        #Only change schema if nothing exist already.
        #Subclasses may have a custom schema constructed
        if not getattr(self, 'schema', False):
            schema_factory = self.get_schema_factory(self.type_name, self.schema_name)
            if not schema_factory:
                err = _(u"Schema type '${type_name}' not registered for content type '${schema_name}'.",
                        mapping = {'type_name': self.type_name, 'schema_name': self.schema_name})
                raise HTTPForbidden(err)
            self.schema = schema_factory()
        result = super(BaseForm, self).__call__()
        return result

    def get_schema_factory(self, type_name, schema_name):
        try:
            return get_content_schemas(self.request.registry)[type_name][schema_name]
        except KeyError:
            pass

    def _tab_fields(self, field):
        results = {}
        for child in field:
            tab = getattr(child.schema, 'tab', '')
            fields = results.setdefault(tab, [])
            fields.append(child)
        return results

    @property
    def tab_titles(self):
        #FIXME adjustable
        from arche.schemas import tabs
        return tabs

    @property
    def form_options(self):
        return {'action': self.request.url,
                'heading': getattr(self, 'heading', ''),
                'tab_fields': self._tab_fields,
                'tab_titles': self.tab_titles}

    def get_bind_data(self):
        return {'context': self.context, 'request': self.request, 'view': self}

    def appstruct(self):
        appstruct = {}
        for field in self.schema.children:
            if hasattr(self.context, field.name):
                val = getattr(self.context, field.name)
                if val is None:
                    val = colander.null
                appstruct[field.name] = val
        return appstruct

    def cancel(self, *args):
        self.flash_messages.add(self.default_cancel)
        return HTTPFound(location = self.request.resource_url(self.context))
    cancel_success = cancel_failure = cancel


class DefaultAddForm(BaseForm):
    schema_name = u'add'
    appstruct = lambda x: {} #No previous values exist :)

    def __call__(self):
        factory = self.get_content_factory(self.type_name)
        if not self.request.has_permission(factory.add_permission):
            raise HTTPForbidden(_(u"You're not allowed to add this content type here. "
                                  u"It requires the permission '%s'" % factory.add_permission))
        return super(DefaultAddForm, self).__call__()

    @property
    def type_name(self):
        return self.request.GET.get('content_type', u'')

    @property
    def heading(self):
        factory =  self.get_content_factory(self.type_name)
        if factory:
            type_title = factory.type_title
        else:
            type_title = self.type_name
        return _(u"Add ${type_title}", mapping = {'type_title': type_title})

    def save_success(self, appstruct):
        self.flash_messages.add(self.default_success, type="success")
        factory = self.get_content_factory(self.type_name)
        obj = factory(**appstruct)
        name = generate_slug(self.context, appstruct['title'])
        self.context[name] = obj
        return HTTPFound(location = self.request.resource_url(obj))


class DefaultEditForm(BaseForm):
    schema_name = u'edit'

    @property
    def type_name(self):
        return self.context.type_name

    @property
    def heading(self):
        return _(u"Edit ${type_title}", mapping = {'type_title': self.context.type_title})

    def save_success(self, appstruct):
        self.flash_messages.add(self.default_success, type="success")
        self.context.update(**appstruct)
        return HTTPFound(location = self.request.resource_url(self.context))


class DefaultDeleteForm(BaseForm):
    appstruct =lambda x: {}
    schema_name = u'delete'
    heading = _(u"Delete")

    @property
    def type_name(self):
        return self.context.type_name

    @property
    def buttons(self):
        return (self.button_delete, self.button_cancel,)

    def get_schema_factory(self, type_name, schema_name):
        """ Allow custom delete schemas here, otherwise just use the default one. """
        schema = get_content_schemas(self.request.registry).get(type_name, {}).get(schema_name)
        if not schema:
            return colander.Schema

    def delete_success(self, appstruct):
        if self.root == self.context:
            raise HTTPForbidden("Can't delete root")
        msg = _(u"Deleted '${title}'",
                mapping = {'title': self.context.title})
        parent = self.context.__parent__
        del parent[self.context.__name__]
        self.flash_messages.add(msg, type = 'warning')
        return HTTPFound(location = self.request.resource_url(parent))


class DynamicView(BaseForm):
    """ Based on view schemas. """
    schema_name = u'view'
    buttons = ()

    @property
    def type_name(self):
        return self.context.type_name

    def show(self, form):
        appstruct = self.appstruct()
        if appstruct is None:
            appstruct = {}
        return {'form': form.render(appstruct = appstruct, readonly = True)}


class DefaultView(BaseView):
    
    def __call__(self):
        return {}
    

def delegate_content_view(context, request):
    view_name = context.default_view and context.default_view or 'view'
    response = render_view_to_response(context, request, name=view_name)
    if response is None:  # pragma: no coverage
        warnings.warn("Failed to look up view called %r for %r." %
                      (view_name, context))
        raise HTTPNotFound()
    return response

def set_view(context, request, name = None):
    name = request.GET.get('name', name)
    if name is None:
        raise ValueError("Need to specify a request with the GET variable name or simply a name parameter.")
    if get_view(context, request, view_name = name) is None:
        raise HTTPForbidden(u"There's no view registered for this content type with that name. "
                            u"Perhaps you forgot to register the view for this context?")
    context.default_view = name
    if name != 'view':
        title = get_content_views(request.registry)[context.type_name][name]
    else:
        title = _(u"Default view")
    fm = get_flash_messages(request)
    fm.add(_(u"View set to '${title}'",
             mapping = {'title': title}))
    return HTTPFound(location = request.resource_url(context))


def includeme(config):
    config.add_view(DefaultAddForm,
                    context = 'arche.interfaces.IContent',
                    name = 'add',
                    permission = security.NO_PERMISSION_REQUIRED, #FIXME: perm check in add
                    renderer = 'arche:templates/form.pt')
    config.add_view(DefaultEditForm,
                    context = 'arche.interfaces.IBase',
                    name = 'edit',
                    permission = security.PERM_EDIT,
                    renderer = 'arche:templates/form.pt')
    config.add_view(DefaultDeleteForm,
                    context = 'arche.interfaces.IBase',
                    name = 'delete',
                    permission = security.PERM_DELETE,
                    renderer = 'arche:templates/form.pt')
    config.add_view(DefaultView,
                    name = 'view',
                    context = 'arche.interfaces.IContent',
                    permission = security.PERM_VIEW,
                    renderer = 'arche:templates/base_view.pt')
    config.add_view(DynamicView,
                    name = 'dynamic_view',
                    context = 'arche.interfaces.IContent', #Should this be used?
                    permission = security.PERM_EDIT,
                    renderer = 'arche:templates/form.pt')
    config.add_view(DynamicView,
                    context = 'arche.interfaces.IBare', #So at least something exist...
                    permission = security.PERM_VIEW,
                    renderer = 'arche:templates/form.pt')
    config.add_view(delegate_content_view,
                    context = 'arche.interfaces.IContent',
                    permission = security.NO_PERMISSION_REQUIRED,
                    )
    config.add_view(set_view,
                    name = 'set_view',
                    context = 'arche.interfaces.IContent',
                    permission = security.PERM_EDIT,
                    )
    config.add_content_view('Document', 'dynamic_view', _(u"Dynamic view"))
