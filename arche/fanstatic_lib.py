from fanstatic import Library
from fanstatic import Resource
from js.jquery import jquery

library = Library('arche', 'static')

main_css = Resource(library, 'main.css')
dropzonejs = Resource(library, 'dropzone.js', depends=(jquery,))
dropzonecss = Resource(library, 'css/dropzone.css', depends=(dropzonejs,))
dropzonebasiccss = Resource(library, 'css/basic.css', depends=(dropzonejs,))


