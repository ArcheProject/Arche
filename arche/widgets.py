import datetime
import random
import string

import colander
from deform.widget import AutocompleteInputWidget
from deform.widget import Select2Widget
from deform.widget import Widget
from deform.widget import filedict
from pyramid.threadlocal import get_current_request
from pyramid.traversal import find_resource
from pyramid.traversal import find_root
from pytz import UTC
from repoze.catalog.query import Eq

from arche import _
from arche.interfaces import IFileUploadTempStore


colander_ts = colander._


class LocalDateTime(colander.DateTime):
    """ Override datetime to be able to handle local timezones and DST.
        - Fetches timezone from dt_handler.timezone
        - Converts deserialized value to UTC
    """

    def _get_tz(self):
        request = get_current_request()
        return request.dt_handler.timezone

    def serialize(self, node, appstruct):
        if not appstruct:
            return colander.null
        if type(appstruct) is datetime.date:  # cant use isinstance; dt subs date
            appstruct = datetime.datetime.combine(appstruct, datetime.time())
        if not isinstance(appstruct, datetime.datetime):
            raise colander.Invalid(node,
                                   colander_ts('"${val}" is not a datetime object',
                                               mapping={'val': appstruct})
                                   )
        if appstruct.tzinfo is None:
            appstruct = appstruct.replace(tzinfo=UTC)
        appstruct = appstruct.astimezone(self._get_tz())
        return appstruct.isoformat()

    def deserialize(self, node, cstruct):
        if not cstruct:
            return colander.null
        try:
            # Note: Don't pass timezone to colander. It will simply attach it
            # and not convert properly which messes up the DST.
            result = colander.iso8601.parse_date(
                cstruct, default_timezone=None)
        except colander.iso8601.ParseError as e:
            raise colander.Invalid(node, colander_ts(self.err_template,
                                                     mapping={'val': cstruct, 'err': e}))
        tzinfo = self._get_tz()
        if getattr(result, 'tzinfo', None) is None:
            result = tzinfo.localize(result)
        return result.astimezone(UTC)  # ALWAYS save UTC!


class TaggingWidget(Select2Widget):
    """ A very liberal widget that allows the user to pretty much enter anything.
        It will also display any existing values.
        
        placeholder
            Text to display when nothing is entered
        
        tags
            Predefined tags that will show up as suggestions

        custom_tags
            Set to False to disable creating new tags
    """
    template = 'select2_tags'
    readonly_template = 'readonly/select2_tags'
    null_value = ''
    placeholder = _("Tags")
    minimumInputLength = 2
    tags = ()
    custom_tags = True
    sortable = False

    @property
    def custom_tags_js(self):
        return self.custom_tags and 'true' or 'false'

    @property
    def multiple(self):
        #Can't be singular for tagging widget
        return True

    def serialize(self, field, cstruct, **kw):
        if self.sortable:
            #FIXME: Deform doesn't use fanstatic. Include some other way?
            from js.jqueryui import ui_sortable
            ui_sortable.need()
        if cstruct in (colander.null, None):
            cstruct = self.null_value
        readonly = kw.get('readonly', self.readonly)
        template = readonly and self.readonly_template or self.template
        tmpl_values = self.get_template_values(field, cstruct, kw)
        tmpl_values['values'] = self.tags
        return field.renderer(template, **tmpl_values)


class ReferenceWidget(Select2Widget):
    """ A reference widget that searches for content to reference.
        It returns a list.
        
        Note! Any default values for this must return an iterator with uids.
        
        query_params
            Things to send to search.json page
            glob: 1 is always a good idea, since it enables search with glob
            type_name: Limit to these content types only. Either a list or a single name as a string.

        multiple
            Disable multiple selection by setting to False

        sortable
            Enable sorting by setting to True. Does not work on sets, obviously.
    """
    template = 'select2_reference'
    readonly_template = 'readonly/select2_reference'
    null_value = ''
    placeholder = _("Type something to search.")
    minimumInputLength = 2
    show_thumbs = True
    default_query_params = {'glob': 1, 'show_hidden': 1, 'limit': 20}
    query_params = {}
    multiple = True
    sortable = False
    id_attr = 'uid'
    allowClear = True
    view_name = "search_select2.json"  # The view to query
    context_from = 'get_root' # Which attribute on view to fetch the context from.
    #Make query view configurable?

    def _fetch_referenced_objects(self, field, cstruct):
        if cstruct in (colander.null, None, ''):
            return []
        view = field.schema.bindings['view']
        root = view.root
        query = root.catalog.query
        address_for_docid = root.document_map.address_for_docid
        results = []
        if self.multiple:
            docids = []
            for uid in cstruct:
                docids.extend(query(Eq(self.id_attr, uid))[1])
        else:
            docids = query(Eq(self.id_attr, cstruct))[1]
        for docid in docids:
            path = address_for_docid(docid)
            obj = find_resource(root, path)
            results.append(obj)
        return results

    def serialize(self, field, cstruct, **kw):
        if self.sortable:
            #FIXME: Deform doesn't use fanstatic. Include some other way?
            from js.jqueryui import ui_sortable
            ui_sortable.need()
        if cstruct in (colander.null, None):
            cstruct = self.null_value
        readonly = kw.get('readonly', self.readonly)
        kw.setdefault("context_from", self.context_from)
        kw.setdefault('view_name', self.view_name)
        kw.setdefault('placeholder', self.placeholder)
        kw.setdefault("minimumInputLength", self.minimumInputLength)
        kw['show_thumbs'] = str(bool(kw.get('show_thumbs', self.show_thumbs))).lower()  # true or false in js
        bindings = field.schema.bindings
        view = bindings['view']
        context_func = getattr(self, kw["context_from"])
        query_context = context_func(bindings)
        template = readonly and self.readonly_template or self.template
        kw.setdefault('request', view.request)
        tmpl_values = self.get_template_values(field, cstruct, kw)
        tmpl_values['values'] = self._fetch_referenced_objects(field, cstruct)
        if not readonly:
            query_params = self.default_query_params.copy()
            query_params.update(self.query_params)
            query_url = view.request.resource_url(query_context, kw['view_name'], query=query_params)
            tmpl_values['query_url'] = query_url
        return field.renderer(template, **tmpl_values)

    def get_root(self, bindings):
        if "view" in bindings:
            return bindings["view"].root
        return find_root(bindings["context"])


# DO NOT use this in colander.Sequence fields. Will not work.
# Use without kw multiple=False instead.
class UserReferenceWidget(ReferenceWidget):
    default_query_params = {'glob': 1,
                            'show_hidden': 1,
                            'id_attr': 'userid',
                            'type_name': 'User'}
    id_attr = 'userid'


class FileAttachmentWidget(Widget):
    """ Show if a file is uploaded, give the option to delete or replace it.
    """
    acceptedMimetypes = None
    template = 'file_upload'
    readonly_template = 'readonly/file_upload'

    @property
    def tmpstore(self):
        request = get_current_request()
        return IFileUploadTempStore(request)

    def random_id(self):
        return ''.join(
            [random.choice(string.ascii_letters) for i in range(10)])

    def serialize(self, field, cstruct, **kw):
        if cstruct in (colander.null, None):
            cstruct = {}
        if cstruct:
            uid = cstruct.get('uid')
            if uid is not None and not uid in self.tmpstore:
                self.tmpstore[uid] = cstruct
        readonly = kw.get('readonly', self.readonly)
        template = readonly and self.readonly_template or self.template
        values = {'view': field.schema.bindings.get('view'),
                  'request': field.schema.bindings.get('request'),
                  'context': field.schema.bindings.get('context')}
        values['blob_key'] = getattr(field.schema, 'blob_key', 'file')
        values.update(self.get_template_values(field, cstruct, kw))
        return field.renderer(template, **values)

    def deserialize(self, field, pstruct):
        if pstruct is colander.null:
            return colander.null
        upload = pstruct.get('upload')
        uid = pstruct.get('uid')

        if hasattr(upload, 'file'):
            # the upload control had a file selected
            data = filedict()
            data['fp'] = upload.file
            filename = upload.filename
            # sanitize IE whole-path filenames
            filename = filename[filename.rfind('\\')+1:].strip()
            data['filename'] = filename
            data['mimetype'] = upload.type
            data['size'] = upload.length
            if uid is None:
                # no previous file exists
                while 1:
                    uid = self.random_id()
                    if self.tmpstore.get(uid) is None:
                        data['uid'] = uid
                        self.tmpstore[uid] = data
                        preview_url = self.tmpstore.preview_url(uid)
                        self.tmpstore[uid]['preview_url'] = preview_url
                        break
            else:
                # a previous file exists
                data['uid'] = uid
                self.tmpstore[uid] = data
                preview_url = self.tmpstore.preview_url(uid)
                self.tmpstore[uid]['preview_url'] = preview_url
        elif pstruct.get('delete') == 'delete':
            data = filedict(delete='delete')
        else:
            # the upload control had no file selected
            if uid is None:
                # no previous file exists
                return colander.null
            else:
                # a previous file should exist
                data = self.tmpstore.get(uid)
                # but if it doesn't, don't blow up
                if data is None:
                    return colander.null
        return data


@colander.deferred
def deferred_autocompleting_userid_widget(node, kw):
    context = kw['context']
    root = find_root(context)
    choices = tuple(root.users.keys())
    return AutocompleteInputWidget(size=15,
                                   values=choices,
                                   min_length=2)
