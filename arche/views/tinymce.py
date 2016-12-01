from pyramid.view import view_config
from repoze.folder import IFolder

from arche.views.base import BaseView


class TinyMCEViews(BaseView):
    @view_config(name="contained_image_list.json", renderer='json')
    def external_image_list(self):
        images = []
        if IFolder.providedBy(self.context):
            for obj in self.context.values():
                if obj.type_name != 'Image':
                    continue
                url = self.request.resource_url(obj, 'inline')
                images.append({'title': obj.title, 'value': url})
            images.sort(key=lambda x: x['title'].lower())
        return images


def includeme(config):
    config.scan(__name__)
