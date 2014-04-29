from deform.widget import FileUploadWidget
from colander import null
from pyramid.threadlocal import get_current_request 
from arche.fanstatic_lib import dropzonejs
from arche.fanstatic_lib import dropzonecss
from arche.fanstatic_lib import dropzonebasiccss

class DropzoneWidget(FileUploadWidget):
    def serialize(self, field, cstruct=None, readonly=False):
        dropzonejs.need()
        dropzonecss.need()
        dropzonebasiccss.need()
        field.dropzoneDefaultMessage = u'Drag and drop your files here'
        field.dropzoneFallbackMessage = u'dropzoneFallbackMessage'
        field.dropzoneFallbackText = u'dropzoneFallbackText'
        field.dropzoneInvalidFileType = u'dropzoneInvalidFileType'
        field.dropzoneFileTooBig = u'dropzoneFileTooBig'
        field.dropzoneResponseError = u'dropzoneResponseError'
        field.dropzoneCancelUpload = u'dropzoneCancelUpload'
        field.dropzoneCancelUploadConfirmation = u'dropzoneCancelUploadConfirmation'
        field.dropzoneRemoveFile = u'dropzoneRemoveFile'
        field.dropzoneMaxFilesExceeded = u'dropzoneMaxFilesExceeded'
        field.request = get_current_request()
        
        return super(DropzoneWidget, self).serialize(field, cstruct=cstruct, readonly=readonly)
        
         
    def deserialize(self, field, pstruct=None):
        if pstruct is null:
            return null
        return self.tmpstore[pstruct]
    