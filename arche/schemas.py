import datetime

from pyramid.threadlocal import get_current_request
import colander
import deform

from arche import _
from arche.interfaces import IPopulator
from arche.utils import get_content_factories
from arche.validators import existing_userid_or_email
from arche.validators import login_password_validator
from arche.validators import unique_email_validator
from arche.validators import unique_userid_validator
from arche.validators import supported_thumbnail_mimetype
from arche.widgets import DropzoneWidget
from arche.widgets import FileAttachmentWidget
from arche.widgets import ReferenceWidget
from arche.widgets import TaggingWidget


class DateTime(colander.DateTime):
    """ Override datetime to be able to handle local timezones and DST.
        Hopefully, this sillyness will change.
    """
    def serialize(self, node, appstruct):
        if not appstruct:
            return colander.null

        if type(appstruct) is datetime.date: # cant use isinstance; dt subs date
            appstruct = datetime.datetime.combine(appstruct, datetime.time())

        if not isinstance(appstruct, datetime.datetime):
            raise colander.Invalid(node,
                          _('"${val}" is not a datetime object',
                            mapping={'val':appstruct})
                          )

        if appstruct.tzinfo is None:
            appstruct = appstruct.replace(tzinfo=self.default_tzinfo)

        request = get_current_request()
        appstruct = request.dt_handler.normalize(appstruct)
        return appstruct.isoformat()

    def deserialize(self, node, cstruct):
        if not cstruct:
            return colander.null

        #Split time and figure out if minutes and seconds  are part of the structure
        pattern = "%Y-%m-%dT"
        time = cstruct.split('T')[1]
        if time:
            parts = ('%H', '%M', '%S')
            pattern += ":".join(parts[:len(time.split(':'))])
        request = get_current_request()
        res = request.dt_handler.string_convert_dt(cstruct, pattern = pattern)
        return request.dt_handler.tz_to_utc(res) #ALWAYS save UTC!


#FIXME: This will change later
tabs = {'': _(u"Default"),
        'visibility': _(u"Visibility"),
        'metadata': _(u"Metadata"),
        'related': _(u"Related"),
        'users': _(u"Users"),
        'groups': _(u"Groups"),}


@colander.deferred
def current_userid(node, kw):
    userid = kw['request'].authenticated_userid
    return userid and userid or colander.null

@colander.deferred
def current_users_uid(node, kw):
    userid = kw['request'].authenticated_userid
    if userid:
        user = kw['view'].root['users'].get(userid)
        if user:
            return (user.uid,)

@colander.deferred
def userid_hinder_widget(node, kw):
    view = kw['view']
    return deform.widget.AutocompleteInputWidget(values = tuple(view.root['users'].keys()))

@colander.deferred
def populators_choice(node, kw):
    request = kw['request']
    class _NoThanks(object):
        title = _('No thanks')
        description = _("Don't install or change anything")
    values = [('', _NoThanks())]
    values.extend([(x.name, x.factory) for x in request.registry.registeredAdapters() if x.provided == IPopulator])
    return deform.widget.RadioChoiceWidget(values = values, template = "widgets/object_radio_choice")

@colander.deferred
def tagging_widget(node, kw):
    view = kw['view']
    #This might be a very dumb way to get unique values...
    tags = tuple(view.root.catalog['tags']._fwd_index.keys())
    return TaggingWidget(tags = tags)

@colander.deferred
def default_now(node, kw):
    request = kw['request']
    return request.dt_handler.utcnow()

def to_lowercase(value):
    if isinstance(value, basestring):
        return value.lower()
    return value

class DCMetadataSchema(colander.Schema):
    title = colander.SchemaNode(colander.String())
    description = colander.SchemaNode(colander.String(),
                                      widget = deform.widget.TextAreaWidget(rows = 5),
                                      missing = u"")
    tags = colander.SchemaNode(colander.List(),
                               title = _("Tags or subjects"),
                               missing = "",
                               tab = 'metadata',
                               widget = tagging_widget)
    creator = colander.SchemaNode(colander.List(),
                                  tab = 'metadata',
                                  widget = ReferenceWidget(query_params = {'type_name': 'User'}),
                                  missing = (),
                                  default = current_users_uid)
    contributor = colander.SchemaNode(colander.List(),
                                      widget = ReferenceWidget(query_params = {'type_name': 'User'}),
                                      tab = 'metadata',
                                      missing = ())
    created = colander.SchemaNode(DateTime(),
                                  default = default_now,
                                  missing = colander.null,
                                  tab = 'metadata')
    relation = colander.SchemaNode(colander.List(),
                                   title = _(u"Related content"),
                                   description = _(u"Can be used to link to other content"),
                                   tab = 'metadata',
                                   missing = (),
                                   widget = ReferenceWidget())
    publisher = colander.SchemaNode(colander.String(),
                                    missing = "",
                                  tab = 'metadata')
    date = colander.SchemaNode(DateTime(),
                               title = _(u"Date"),
                               description = _(u"Publish date, or used for sorting"),
                               default = default_now,
                               missing = colander.null,
                               tab = 'metadata')
    rights = colander.SchemaNode(colander.String(),
                                 title = _(u"Licensing"),
                                 missing = u"",
                                 tab = 'metadata')
    #type?
    #format
    #identifier -> url
    #source
    #language

@colander.deferred
def default_factory_attr(node, kw):
    """ This probably won't fire unless you add something,
        but it might be useful for other forms aswell.
    """
    request = kw['request']
    if request.view_name == 'add':
        content_type = request.GET.get('content_type')
        factory = get_content_factories()[content_type]
        return getattr(factory, node.name)
    getattr(kw['context'], node.name)


class BaseSchema(colander.Schema):
    nav_visible = colander.SchemaNode(colander.Bool(),
                                      title = _(u"Show in navigations"),
                                      missing = colander.null,
                                      default = default_factory_attr,
                                      tab = tabs['visibility'])
    listing_visible = colander.SchemaNode(colander.Bool(),
                                          title = _(u"Show in listing or table views"),
                                          description = _(u"The content view will always show this regardless of what you set."),
                                          missing = colander.null,
                                          default = default_factory_attr,
                                          tab = tabs['visibility'])
    search_visible = colander.SchemaNode(colander.Bool(),
                                         title = _(u"Include in search results"),
                                         description = _(u"Note that this is not a permission setting - it's just a matter of practicality for users. "
                                                         u"They may even disable this setting."),
                                         missing = colander.null,
                                         default = default_factory_attr,
                                         tab = tabs['visibility'])


class DocumentSchema(BaseSchema, DCMetadataSchema):
    body = colander.SchemaNode(colander.String(),
                               widget = deform.widget.RichTextWidget(),
                               missing = u"")
    image_data = colander.SchemaNode(deform.FileData(),
                                         missing = None,
                                         title = _(u"Image"),
                                         blob_key = 'image',
                                         validator = supported_thumbnail_mimetype,
                                         widget = FileAttachmentWidget())
    show_byline = colander.SchemaNode(colander.Bool(),
                                      default = True,
                                      tab = tabs['visibility'],
                                      title = _(u"Show byline"),
                                      description = u"If anything exist that will render a byline, like the Byline portlet.",)


class UserSchema(colander.Schema):
    first_name = colander.SchemaNode(colander.String(),
                                     title = _(u"First name"),
                                     missing = u"")
    last_name = colander.SchemaNode(colander.String(),
                                    title = _(u"Last name"),
                                    missing = u"")
    email = colander.SchemaNode(colander.String(),
                                title = _(u"Email adress"),
                                validator = colander.Email())
    image_data = colander.SchemaNode(deform.FileData(),
                                       missing = colander.null,
                                       blob_key = 'image',
                                       title = _(u"Profile image"),
                                       validator = supported_thumbnail_mimetype,
                                       widget = FileAttachmentWidget())
    

class AddUserSchema(UserSchema):
    userid = colander.SchemaNode(colander.String(),
                                 validator = unique_userid_validator)
    password = colander.SchemaNode(colander.String(),
                                   title = _(u"Password"),
                                   widget = deform.widget.CheckedPasswordWidget())


class GroupSchema(colander.Schema):
    title = colander.SchemaNode(colander.String(),
                                title = _(u"Title"))
    description = colander.SchemaNode(colander.String(),
                                      title = _(u"Description"),
                                      widget = deform.widget.TextAreaWidget(rows = 5),
                                      missing = u"")
    members = colander.SchemaNode(
                  colander.Sequence(),
                  colander.SchemaNode(
                          colander.String(),
                          title = _(u"UserID"),
                          name = u"not_used",
                          widget = userid_hinder_widget,),
                  title = _(u"Members"),
                  )


class ChangePasswordSchema(colander.Schema):
    #FIXME: Validate old password
    password = colander.SchemaNode(colander.String(),
                                   title = _(u"Password"),
                                   widget = deform.widget.CheckedPasswordWidget())


class InitialSetup(colander.Schema):
    title = colander.SchemaNode(colander.String(),
                                title = _(u"Site title"),
                                default = _(u"A site made with Arche"))
    userid = colander.SchemaNode(colander.String(),
                                 title = _(u"Admin userid"),
                                 default = u"admin")
    email = colander.SchemaNode(colander.String(),
                                title = _(u"Admins email adress"),
                                validator = colander.Email())
    password = colander.SchemaNode(colander.String(),
                                   title = _(u"Admins password"),
                                   widget = deform.widget.CheckedPasswordWidget())
    populator_name = colander.SchemaNode(colander.String(),
                                         missing = u'',
                                         title = _("Populate site"),
                                         widget = populators_choice)


class LoginSchema(colander.Schema):
    validator = login_password_validator
    email_or_userid = colander.SchemaNode(colander.String(),
                                          preparer = to_lowercase,
                                          title = _(u"Email or UserID"),)
    password = colander.SchemaNode(colander.String(),
                                   title = _(u"Password"),
                                   widget = deform.widget.PasswordWidget())


class RegistrationSchema(colander.Schema):
    email = colander.SchemaNode(colander.String(),
                                title = _(u"Email"),
                                preparer = to_lowercase,
                                validator = unique_email_validator)


class FinishRegistrationSchema(colander.Schema):
    userid = colander.SchemaNode(colander.String(),
                                 title = _(u"UserID"),
                                 preparer = to_lowercase,
                                 validator = unique_userid_validator)
    password = colander.SchemaNode(colander.String(),
                                   title = _(u"Password"),
                                   widget = deform.widget.CheckedPasswordWidget(redisplay = True))


class RecoverPasswordSchema(colander.Schema):
    email_or_userid = colander.SchemaNode(colander.String(),
                                          validator = existing_userid_or_email,
                                          title = _(u"Email or UserID"),)


class RootSchema(BaseSchema, DCMetadataSchema):
    footer = colander.SchemaNode(colander.String(),
                                 title = _("Footer"),
                                 widget = deform.widget.RichTextWidget(delayed_load = True))

@colander.deferred
def default_blob_key(node, kw):
    context = kw['context']
    return getattr(context, 'blob_key', 'file')


class AddFileSchema(BaseSchema, DCMetadataSchema):
    title = colander.SchemaNode(colander.String(),
                                title = _("Title"),
                                description = _("Filename will be used if you leave this blank"),
                                missing = u"")
    file_data = colander.SchemaNode(deform.FileData(),
                                    title = _(u"Upload file"),
                                    blob_key = default_blob_key,
                                    widget = FileAttachmentWidget())


class EditFileSchema(AddFileSchema, DCMetadataSchema):
    file_data = colander.SchemaNode(deform.FileData(),
                                    title = _(u"Change file"),
                                    missing = colander.null,
                                    blob_key = default_blob_key,
                                    widget = FileAttachmentWidget())


class LinkSchema(BaseSchema):
    target = colander.SchemaNode(colander.String(),
                                 validator = colander.url)
    title = colander.SchemaNode(colander.String(),
                                missing = u"")
    description = colander.SchemaNode(colander.String(),
                                      missing = u"")


class AddLinkSchema(LinkSchema):
    name = colander.SchemaNode(colander.String(), #Special validator based on permission?
                           )


class SiteSettingsSchema(colander.Schema):
    allow_self_registration = colander.SchemaNode(colander.Bool(),
                                                  title = _(u"Allow users to register themselves to this site."),
                                                  default = False)


def includeme(config):
    config.add_content_schema('Document', DocumentSchema, ('view', 'edit', 'add'))
    config.add_content_schema('User', UserSchema, ('view', 'edit'))
    config.add_content_schema('User', AddUserSchema, 'add')
    config.add_content_schema('User', ChangePasswordSchema, 'change_password')
    config.add_content_schema('InitialSetup', InitialSetup, 'setup')
    config.add_content_schema('Auth', LoginSchema, 'login')
    config.add_content_schema('Auth', RegistrationSchema, 'register')
    config.add_content_schema('Auth', FinishRegistrationSchema, 'register_finish')
    config.add_content_schema('Auth', RecoverPasswordSchema, 'recover_password')
    config.add_content_schema('Group', GroupSchema, ('add', 'view', 'edit'))
    config.add_content_schema('File', AddFileSchema, 'add')
    config.add_content_schema('File', EditFileSchema, 'edit')
    config.add_content_schema('Image', AddFileSchema, 'add') #Specific schema?
    config.add_content_schema('Image', EditFileSchema, 'edit')
    config.add_content_schema('Root', RootSchema, 'edit')
    config.add_content_schema('Root', SiteSettingsSchema, 'site_settings')
    config.add_content_schema('Link', AddLinkSchema, 'add')
    config.add_content_schema('Link', LinkSchema, 'edit')
