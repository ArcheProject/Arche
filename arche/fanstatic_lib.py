from fanstatic import Library
from fanstatic import Resource
from js.jquery import jquery
from js.bootstrap import bootstrap_css

library = Library('arche', 'static')

main_css = Resource(library, 'main.css', depends = (bootstrap_css,))
dropzonejs = Resource(library, 'dropzone.js', depends=(jquery,))
dropzonecss = Resource(library, 'css/dropzone.css', depends=(dropzonejs,))
dropzonebootstrapcss = Resource(library, 'css/dropzone-bootstrap.css', depends=(dropzonejs,))
dropzonebasiccss = Resource(library, 'css/basic.css', depends=(dropzonejs,))

common_js = Resource(library, 'common.js', depends = (jquery,))
