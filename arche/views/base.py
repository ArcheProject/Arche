from __future__ import unicode_literals
import warnings

from BTrees.OOBTree import OOBTree
from betahaus.viewcomponent import render_view_group
from deform_autoneed import need_lib
from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPNotFound
from pyramid.renderers import get_renderer
from pyramid.renderers import render
from pyramid.traversal import find_resource
from pyramid.traversal import find_root
from pyramid.traversal import lineage
from pyramid.view import render_view_to_response
from pyramid_deform import FormView
from zope.component.event import objectEventNotify
from zope.interface import implementer
import colander
import deform

from arche import _
from arche import security
from arche.events import SchemaCreatedEvent
from arche.events import ViewInitializedEvent
from arche.fanstatic_lib import common_js
from arche.fanstatic_lib import html5shiv_js
from arche.fanstatic_lib import main_css
from arche.fanstatic_lib import picturefill_js
from arche.fanstatic_lib import respond_js
from arche.interfaces import IBaseView
from arche.interfaces import IContentView
from arche.interfaces import IFolder
from arche.interfaces import IThumbnails
from arche.portlets import get_portlet_manager
from arche.utils import generate_slug
from arche.utils import get_addable_content
from arche.utils import get_content_factories
from arche.utils import get_content_schemas
from arche.utils import get_content_views
from arche.utils import get_flash_messages
from arche.utils import get_view


@implementer(IBaseView)
class BaseView(object):
    
    def __init__(self, context, request):
        self.context = context
        self.request = request
        need_lib('basic')
        main_css.need()
        common_js.need()
        picturefill_js.need()
        html5shiv_js.need()
        respond_js.need()
        view_event = ViewInitializedEvent(self)
        objectEventNotify(view_event)

    @property
    def root(self):
        return self.request.root

    @reify
    def flash_messages(self):
        return get_flash_messages(self.request)

    @reify
    def profile(self):
        """ Note: this attr may change or move.
        """
        userid = self.request.authenticated_userid
        if userid:
            return self.root['users'].get(userid, None)

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

    def catalog_search(self, resolve = False, perm = security.PERM_VIEW, **kwargs):
        results = self.root.catalog.search(**kwargs)[1]
        if resolve:
            results = self.resolve_docids(results, perm = perm)
        return results

    def catalog_query(self, query, resolve = False, perm = security.PERM_VIEW, **kwargs):
        results = self.root.catalog.query(query, **kwargs)[1]
        if resolve:
            results = self.resolve_docids(results, perm = perm)
        return results

    def resolve_docids(self, docids, perm = security.PERM_VIEW):
        if isinstance(docids, basestring):
            docids = (docids,)
        for docid in docids:
            path = self.root.document_map.address_for_docid(docid)
            obj = find_resource(self.root, path)
            #FIXME: Have perm check here?
            if perm and not self.request.has_permission(perm, obj):
                continue
            yield obj

    def resolve_uid(self, uid, perm = security.PERM_VIEW):
        for obj in self.catalog_search(resolve = True, uid = uid, perm = perm):
            return obj

    def breadcrumbs(self):
        return reversed(list(lineage(self.context)))

    def get_content_factory(self, name):
        return get_content_factories(self.request.registry).get(name)

    def macro(self, asset_spec, xhr_asset = None, macro_name='main'):
        if xhr_asset and self.request.is_xhr:
            asset_spec = xhr_asset
        return get_renderer(asset_spec).implementation().macros[macro_name]

    def addable_content(self, context):
        _marker = object()
        context_type = getattr(context, 'type_name', None)
        factories = get_content_factories(self.request.registry)
        for (name, addable) in get_addable_content(self.request.registry).items():
            if context_type in addable:
                factory = factories.get(name, None)
                if factory is not None:
                    add_perm = getattr(factory, 'add_permission', _marker)
                    if self.request.has_permission(add_perm, context):
                        yield factory

    def render_template(self, renderer, **kwargs):
        kwargs.setdefault('view', self)
        return render(renderer, kwargs, self.request)

    def render_actionbar(self, context):
        if self.request.authenticated_userid:
            return self.render_template('arche:templates/action_bar.pt')

    def render_view_group(self, group, context = None, **kw):
        if context is None:
            context = self.context
        return render_view_group(context, self.request, group, view = self, **kw)

    def get_local_nav_objects(self, context):
        #FIXME: Conditions for navigation!
        if IFolder.providedBy(context):
            for obj in context.values():
                if getattr(obj, 'nav_visible', False):
                    if self.request.has_permission(security.PERM_VIEW, obj):
                        yield obj

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

    def thumb_tag(self, context, scale_name, default = u"", extra_cls = '', direction = "thumb", key = "image", **kw):
        #FIXME: Default?
        url = self.request.thumb_url(context, scale_name, key = key)
        if not url:
            return default
        thumbnails = self.request.registry.queryAdapter(context, IThumbnails)
        if thumbnails is None:
            return default
        thumb = thumbnails.get_thumb(scale_name, direction = direction, key = key)
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


@implementer(IContentView)
class ContentView(BaseView):
    """ Use this for more complex views that can have settings and be dynamically selected
        as a view for content types
    """
    title = ""
    description = ""
    settings_schema = None

    @property
    def settings(self):
        return getattr(self.context, '__view_settings__', {})
    @settings.setter
    def settings(self, value):
        self.context.__view_settings__ = OOBTree(value)


class BaseForm(BaseView, FormView):
    default_success = _(u"Done")
    default_cancel = _(u"Canceled")
    schema_name = ""
    type_name = ""
    title = None
    formid = 'deform'

    button_delete = deform.Button('delete', title = _("Delete"), css_class = 'btn btn-danger')
    button_cancel = deform.Button('cancel', title = _("Cancel"), css_class = 'btn btn-default')
    button_save = deform.Button('save', title = _("Save"), css_class = 'btn btn-primary')
    button_add = deform.Button('add', title = _("Add"), css_class = 'btn btn-primary')

    buttons = (button_save, button_cancel,)

    def __call__(self):
        #Only change schema if nothing exist already.
        #Subclasses may have a custom schema constructed
        if not getattr(self, 'schema', False):
            schema_factory = self.get_schema_factory(self.type_name, self.schema_name)
            if not schema_factory:
                err = "Schema type '%s' not registered for content type '%s'." %\
                      (self.schema_name, self.type_name)
                raise HTTPForbidden(err)
            self.schema = schema_factory()
            event = SchemaCreatedEvent(self.schema)
            objectEventNotify(event)
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
                'heading': self.get_schema_heading(),
                'tab_fields': self._tab_fields,
                'tab_titles': self.tab_titles,
                'formid': self.formid}

    def get_schema_heading(self):
        if getattr(self, 'title', None) is not None:
            return self.title
        return getattr(self.schema, 'title', '')

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
        if factory is None:
            raise HTTPNotFound()
        if not self.request.has_permission(factory.add_permission):
            raise HTTPForbidden(_("You're not allowed to add this content type here. "
                                  "It requires the permission '%s'" % factory.add_permission))
        return super(DefaultAddForm, self).__call__()

    @property
    def type_name(self):
        return self.request.GET.get('content_type', u'')

    @property
    def title(self):
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
        naming_attr = getattr(obj, 'naming_attr', 'title')
        name = generate_slug(self.context, getattr(obj, naming_attr, ''))
        self.context[name] = obj
        return HTTPFound(location = self.request.resource_url(obj))


class DefaultEditForm(BaseForm):
    schema_name = u'edit'

    @property
    def type_name(self):
        return self.context.type_name

    @property
    def title(self):
        return _("Edit ${type_title}", mapping = {'type_title': self.context.type_title})

    def save_success(self, appstruct):
        self.flash_messages.add(self.default_success, type="success")
        self.context.update(**appstruct)
        return HTTPFound(location = self.request.resource_url(self.context))


class DefaultDeleteForm(BaseForm):
    appstruct =lambda x: {}
    schema_name = u'delete'
    
    @property
    def title(self):
        return _("Delete " + self.context.title + " ( " + self.context.type_name + " ) ?")

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
        if hasattr(self.context, 'is_permanent'):
            raise HTTPForbidden("Can't delete this object because it is permanent.")
        msg = _("Deleted '${title}'",
                mapping = {'title': self.context.title})
        parent = self.context.__parent__
        del parent[self.context.__name__]
        self.flash_messages.add(msg, type = 'warning')
        return HTTPFound(location = self.request.resource_url(parent))


class DynamicView(BaseForm, ContentView):
    """ Based on view schemas. """
    schema_name = u'view'
    buttons = ()
    title = _("Dynamic view")

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
        view_cls = get_content_views(request.registry)[context.type_name][name]
        title = getattr(view_cls, 'title', name)
    else:
        title = _("Default view")
    fm = get_flash_messages(request)
    fm.add(_("View set to '${title}'",
             mapping = {'title': title}))
    #Remove settings. Should this be a subscriber instead? It's a bit destructive too, especially if clearing this isn't needed
    if hasattr(context, '__view_settings__'):
        delattr(context, '__view_settings__')
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
                    renderer = 'arche:templates/content/basic.pt')
    config.add_view(DynamicView,
                    name = 'dynamic_view',
                    context = 'arche.interfaces.IContent', #Should this be used?
                    permission = security.PERM_EDIT,
                    renderer = 'arche:templates/form.pt')
    config.add_view(DynamicView,
                    context = 'arche.interfaces.IBase', #So at least something exist...
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
    config.add_content_view('Document', 'dynamic_view', DynamicView)
