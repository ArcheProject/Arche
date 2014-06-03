from bs4 import BeautifulSoup
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound
import requests

from arche import _
from arche import security
from arche.interfaces import IRoot
from arche.utils import generate_slug
from arche.views.base import ContentView
from arche.views.base import DefaultAddForm


def embed_query(context, request):
    #FIXME: think about security here. Is it a bad idea to have this open?
    url = request.params.get('url', None)
    try:
        response = requests.get(url, verify = False) #FIXME: We need root certs to make this work!
    except requests.exceptions.RequestException as e:
        raise HTTPForbidden(str(e))
    if 'application/json' not in response.headers.get('content-type'):
        url = _resolve_oembed_url(response)
        try:
            response = requests.get(url, verify = False)
        except requests.exceptions.RequestException as e:
            raise HTTPForbidden(str(e))
    if response.status_code != 200:
        raise HTTPForbidden(_("Server didn't return a response I could understand"))
    result = response.json()
    result['oembed_json_url'] = url
    return result

def _resolve_oembed_url(response):
    soup = BeautifulSoup(response.content)
    tags = soup.head.findAll(type = 'application/json+oembed')
    if not tags:
        raise HTTPForbidden()
    oembed_url = tags[0].get('href', None)
    if not oembed_url:
        raise HTTPForbidden()
    return oembed_url


class ExternalResourceView(ContentView):

    def __call__(self):
        return {}


class AddExternalResourceForm(DefaultAddForm):
    type_name = u"ExternalResource"
    
    def save_success(self, appstruct):
        self.flash_messages.add(self.default_success, type="success")
        factory = self.get_content_factory(self.type_name)
        obj = factory(**appstruct)
        name = generate_slug(self.context, obj.title)
        self.context[name] = obj
        return HTTPFound(location = self.request.resource_url(obj))


def includeme(config):
    config.add_view(embed_query,
                    context = IRoot,
                    name = 'embed_query.json',
                    renderer = 'json')
    config.add_view(ExternalResourceView,
                    context = 'arche.interfaces.IExternalResource',
                    permission = security.PERM_VIEW,
                    renderer = 'arche:templates/content/external_resource.pt')
    config.add_view(AddExternalResourceForm,
                    context = 'arche.interfaces.IContent',
                    name = 'add',
                    request_param = "content_type=ExternalResource",
                    permission = security.NO_PERMISSION_REQUIRED,
                    renderer = 'arche:templates/form.pt')
    