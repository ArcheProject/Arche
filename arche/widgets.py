import string
import random

from deform.widget import AutocompleteInputWidget
from deform.widget import FileUploadWidget
from deform.widget import Select2Widget
from deform.widget import Widget
from deform.widget import filedict
from pyramid.threadlocal import get_current_request
from pyramid.traversal import find_resource
from pyramid.traversal import find_root
from repoze.catalog.query import Eq
import colander

from arche import _
from arche.fanstatic_lib import dropzonebasiccss
from arche.fanstatic_lib import dropzonebootstrapcss
from arche.fanstatic_lib import dropzonecss
from arche.fanstatic_lib import dropzonejs
from arche.interfaces import IFileUploadTempStore


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

    @property
    def custom_tags_js(self):
        return self.custom_tags and 'true' or 'false'

    @property
    def multiple(self):
        #Can't be singular for tagging widget
        return True

    def serialize(self, field, cstruct, **kw):
        if cstruct in (colander.null, None):
            cstruct = self.null_value
        readonly = kw.get('readonly', self.readonly)
        template = readonly and self.readonly_template or self.template
        tmpl_values = self.get_template_values(field, cstruct, kw)
        tmpl_values['values'] = self.tags
        return field.renderer(template, **tmpl_values)


# FIXME: Needs cleanup and documentation
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
    default_query_params = {'glob': 1, 'show_hidden': 1}
    query_params = {}
    multiple = True
    sortable = False
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
                docids.extend(query(Eq('uid', uid))[1])
        else:
            docids = query(Eq('uid', cstruct))[1]
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
        kw['placeholder'] = kw.get('placeholder', self.placeholder)
        kw['minimumInputLength'] = kw.get('minimumInputLength', self.minimumInputLength)
        kw['show_thumbs'] = str(bool(kw.get('show_thumbs', self.show_thumbs))).lower()  # true or false in js
        view = field.schema.bindings['view']
        template = readonly and self.readonly_template or self.template
        kw.setdefault('request', view.request)
        tmpl_values = self.get_template_values(field, cstruct, kw)
        tmpl_values['values'] = self._fetch_referenced_objects(field, cstruct)
        if not readonly:
            query_params = self.default_query_params.copy()
            query_params.update(self.query_params)
            query_url = view.request.resource_url(view.root, 'search.json', query=query_params)
            tmpl_values['query_url'] = query_url
        return field.renderer(template, **tmpl_values)


class DropzoneWidget(FileUploadWidget):
    """ All of the class attributes can be overridden in the widget.
    """
    maxFilesize = 100 # in Mb
    maxFiles = 1 # 'null' for infinite
    acceptedFiles = "image/png,image/*" #What's a sane default here? Where should it be configured?
    
    dropzoneDefaultMessage = u'Drag and drop your files here'
    dropzoneFallbackMessage = u'dropzoneFallbackMessage'
    dropzoneFallbackText = u'dropzoneFallbackText'
    dropzoneInvalidFileType = u'dropzoneInvalidFileType'
    dropzoneFileTooBig = u'dropzoneFileTooBig'
    dropzoneResponseError = u'dropzoneResponseError'
    dropzoneCancelUpload = u'dropzoneCancelUpload'
    dropzoneCancelUploadConfirmation = u'dropzoneCancelUploadConfirmation'
    dropzoneRemoveFile = u'dropzoneRemoveFile'
    dropzoneMaxFilesExceeded = u'dropzoneMaxFilesExceeded'

    @property
    def acceptedMimetypes(self):
        """ Deprecated property in Dropzone js, but used here to figure out mimetype. """
        return string.split(self.acceptedFiles, ',')

    def serialize(self, field, cstruct=None, readonly=False):
        dropzonejs.need()
        #dropzonecss.need()
        dropzonebootstrapcss.need()
        dropzonebasiccss.need()
        field.request = get_current_request()
        field.hasfile = 'false'
        field.filename = ''
        field.filesize = 0
        if hasattr(field.request.context, '__blobs__') and field.request.context.__blobs__.has_key('file'):
            field.hasfile = 'true'
            field.filename = field.request.context.__blobs__.get('file').filename
            field.filesize = field.request.context.__blobs__.get('file').size
        return super(DropzoneWidget, self).serialize(field, cstruct=cstruct, readonly=readonly)

    def deserialize(self, field, pstruct=None):
        if pstruct is colander.null:
            return colander.null
        mimetype = self.tmpstore[pstruct]['mimetype']
        if mimetype in self.acceptedMimetypes or string.split(mimetype, '/')[0]+'/*' in self.acceptedMimetypes:
            return self.tmpstore[pstruct]
        return colander.null


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
            [random.choice(string.letters) for i in range(10)])

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
