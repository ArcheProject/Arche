from urllib import unquote
import datetime

from pyramid.threadlocal import get_current_request
from pytz import common_timezones
import colander
import deform

from arche import _
from arche.interfaces import IPopulator
from arche.utils import get_content_factories
from arche.validators import deferred_current_password_validator
from arche.validators import existing_userid_or_email
from arche.validators import login_password_validator
from arche.validators import supported_thumbnail_mimetype
from arche.validators import unique_email_validator
from arche.validators import new_userid_validator
from arche.widgets import DropzoneWidget
from arche.widgets import FileAttachmentWidget
from arche.widgets import ReferenceWidget
from arche.widgets import TaggingWidget


colander_ts = colander._


class LocalDateTime(colander.DateTime):
    """ Override datetime to be able to handle local timezones and DST.
        - Fetches timezone from dt_handler.timezone
        - Converts deserialized value to widgets default_timezone (Which should always be UTC)
    """

    def _get_tz(self):
        request = get_current_request()
        return request.dt_handler.timezone

    def serialize(self, node, appstruct):
        if not appstruct:
            return colander.null
        if type(appstruct) is datetime.date: # cant use isinstance; dt subs date
            appstruct = datetime.datetime.combine(appstruct, datetime.time())
        if not isinstance(appstruct, datetime.datetime):
            raise colander.Invalid(node,
                          colander_ts('"${val}" is not a datetime object',
                            mapping={'val':appstruct})
                          )
        if appstruct.tzinfo is None:
            appstruct = appstruct.replace(tzinfo=self.default_tzinfo)
        appstruct = appstruct.astimezone(self._get_tz())
        return appstruct.isoformat()

    def deserialize(self, node, cstruct):
        if not cstruct:
            return colander.null
        try:
            result = colander.iso8601.parse_date(
                cstruct, default_timezone = self._get_tz())
        except colander.iso8601.ParseError as e:
            raise colander.Invalid(node, colander_ts(self.err_template,
                                                     mapping={'val':cstruct, 'err':e}))
        return result.astimezone(self.default_tzinfo) #ALWAYS save UTC!


#FIXME: This will change later
tabs = {'': _(u"Default"),
        'visibility': _(u"Visibility"),
        'metadata': _(u"Metadata"),
        'related': _(u"Related"),
        'users': _(u"Users"),
        'groups': _(u"Groups"),
        'advanced': _("Advanced")}


@colander.deferred
def current_userid(node, kw):
    userid = kw['request'].authenticated_userid
    return userid and userid or colander.null

@colander.deferred
def current_userid_as_tuple(node, kw):
    userid = kw['request'].authenticated_userid
    return userid and (userid,) or colander.null

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
    return deform.widget.RadioChoiceWidget(values = values, template = "object_radio_choice")

@colander.deferred
def tagging_widget(node, kw):
    view = kw['view']
    #This might be a very dumb way to get unique values...
    tags = tuple(view.root.catalog['tags']._fwd_index.keys())
    return TaggingWidget(tags = tags)

@colander.deferred
def tagging_userids_widget(node, kw):
    view = kw['view']
    userids = tuple(view.root['users'].keys())
    return TaggingWidget(tags = userids, placeholder = _("Type to search for UserIDs"))
    

@colander.deferred
def default_now(node, kw):
    request = kw['request']
    return request.dt_handler.localnow()

def to_lowercase(value):
    if isinstance(value, basestring):
        return value.lower()
    return value

class DCMetadataSchema(colander.Schema):
    title = colander.SchemaNode(colander.String())
    description = colander.SchemaNode(colander.String(),
                                      widget = deform.widget.TextAreaWidget(rows = 3),
                                      missing = u"")
    tags = colander.SchemaNode(colander.List(),
                               title = _("Tags or subjects"),
                               missing = "",
                               tab = 'metadata',
                               widget = tagging_widget)
    creator = colander.SchemaNode(colander.List(),
                                  tab = 'metadata',
                                  widget = tagging_userids_widget,
                                  missing = (),
                                  default = current_userid_as_tuple)
    contributor = colander.SchemaNode(colander.List(),
                                      widget = tagging_userids_widget,
                                      tab = 'metadata',
                                      missing = ())
    created = colander.SchemaNode(LocalDateTime(),
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
    date = colander.SchemaNode(LocalDateTime(),
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
                                      tab = 'visibility')
    listing_visible = colander.SchemaNode(colander.Bool(),
                                          title = _(u"Show in listing or table views"),
                                          description = _(u"The content view will always show this regardless of what you set."),
                                          missing = colander.null,
                                          default = default_factory_attr,
                                          tab = 'visibility')
    search_visible = colander.SchemaNode(colander.Bool(),
                                         title = _(u"Include in search results"),
                                         description = _(u"Note that this is not a permission setting - it's just a matter of practicality for users. "
                                                         u"They may even disable this setting."),
                                         missing = colander.null,
                                         default = default_factory_attr,
                                         tab = 'visibility')
    nav_title = colander.SchemaNode(colander.String(),
         title = _(u"Navigation bar title"),
         description = _("If you wish to use another name for when it's shown in menus."),
         missing = "",
         tab = 'metadata')


class DocumentSchema(BaseSchema, DCMetadataSchema):
    body = colander.SchemaNode(colander.String(),
                               widget = deform.widget.RichTextWidget(height = 300),
                               missing = u"")
    image_data = colander.SchemaNode(deform.FileData(),
                                         missing = None,
                                         title = _(u"Image"),
                                         blob_key = 'image',
                                         validator = supported_thumbnail_mimetype,
                                         widget = FileAttachmentWidget())
    show_byline = colander.SchemaNode(colander.Bool(),
                                      default = True,
                                      tab = 'visibility',
                                      title = _(u"Show byline"),
                                      description = u"If anything exist that will render a byline, like the Byline portlet.",)


@colander.deferred
def deferred_timezone_description(node, kw):
    request = kw['request']
    return _("Current default timezone is: '${tzname}', leave this field blank if your're okay with that.",
             mapping = {'tzname': request.dt_handler.get_default_tzname()})

@colander.deferred
def deferred_timezone_validator(node, kw):
    return colander.OneOf(common_timezones)

@colander.deferred
def deferred_timezone_widget(node, kw):
    return deform.widget.AutocompleteInputWidget(size=60,
                                                 values = list(common_timezones), #It's a lazy list
                                                 min_length=1)


class UserSchema(colander.Schema):
    first_name = colander.SchemaNode(colander.String(),
                                     title = _(u"First name"),
                                     missing = u"")
    last_name = colander.SchemaNode(colander.String(),
                                    title = _(u"Last name"),
                                    missing = u"")
    email = colander.SchemaNode(colander.String(),
                                title = _(u"Email adress"),
                                preparer = to_lowercase,
                                validator = unique_email_validator)
    image_data = colander.SchemaNode(deform.FileData(),
                                     missing = colander.null,
                                     blob_key = 'image',
                                     title = _(u"Profile image"),
                                     validator = supported_thumbnail_mimetype,
                                     widget = FileAttachmentWidget())
    timezone = colander.SchemaNode(colander.String(),
                                   title = _("Set custom timezone"),
                                   description = deferred_timezone_description,
                                   validator = deferred_timezone_validator,
                                   widget = deferred_timezone_widget,
                                   missing = "",
                                   default = "",
                                   tab = "advanced")
    

class AddUserSchema(UserSchema):
    userid = colander.SchemaNode(colander.String(),
                                 title = _("UserID"),
                                 validator = new_userid_validator)
    password = colander.SchemaNode(colander.String(),
                                   title = _(u"Password"),
                                   widget = deform.widget.CheckedPasswordWidget())


class GroupSchema(colander.Schema):
    title = colander.SchemaNode(colander.String(),
                                title = _(u"Title"))
    description = colander.SchemaNode(colander.String(),
                                      title = _(u"Description"),
                                      widget = deform.widget.TextAreaWidget(rows = 3),
                                      missing = u"")
    members = colander.SchemaNode(
                  colander.Sequence(),
                  colander.SchemaNode(
                          colander.String(),
                          title = _(u"UserID"),
                          name = u"not_used",
                          widget = userid_hinder_widget,),
                  title = _(u"Members"),)


class ChangePasswordSchema(colander.Schema):
    #Note: Current password field should be removed when token validation or similar is used.
    current_password = colander.SchemaNode(colander.String(),
                                   title = _('Current password'),
                                   widget = deform.widget.PasswordWidget(size=20),
                                   validator = deferred_current_password_validator)
    password = colander.SchemaNode(colander.String(),
                                   title = _(u"Password"),
                                   widget = deform.widget.CheckedPasswordWidget())


class InitialSetup(colander.Schema):
    title = colander.SchemaNode(colander.String(),
                                title = _(u"Site title"),
                                default = _(u"A site made with Arche"))
    userid = colander.SchemaNode(colander.String(),
                                 title = _(u"Admin userid - use lowercase!"),
                                 default = u"admin")
    email = colander.SchemaNode(colander.String(),
                                title = _(u"Email adress"),
                                preparer = to_lowercase,
                                validator = colander.Email())
    password = colander.SchemaNode(colander.String(),
                                   title = _(u"Password"),
                                   widget = deform.widget.CheckedPasswordWidget())
    populator_name = colander.SchemaNode(colander.String(),
                                         missing = u'',
                                         title = _("Populate site"),
                                         widget = populators_choice)


@colander.deferred
def deferred_referer(node, kw):
    request = kw['request']
    return unquote(request.GET.get('came_from', '/'))


class LoginSchema(colander.Schema):
    validator = login_password_validator
    email_or_userid = colander.SchemaNode(colander.String(),
                                          preparer = to_lowercase,
                                          title = _(u"Email or UserID"),)
    password = colander.SchemaNode(colander.String(),
                                   title = _(u"Password"),
                                   widget = deform.widget.PasswordWidget())
    came_from = colander.SchemaNode(colander.String(),
                               missing = "",
                               widget = deform.widget.HiddenWidget(),
                               default = deferred_referer)


class RegistrationSchema(colander.Schema):
    email = colander.SchemaNode(colander.String(),
                                title = _(u"Email"),
                                preparer = to_lowercase,
                                validator = unique_email_validator)


class FinishRegistrationSchema(colander.Schema):
    userid = colander.SchemaNode(colander.String(),
                                 title = _(u"UserID"),
                                 validator = new_userid_validator)
    first_name = colander.SchemaNode(colander.String(),
                                     title = _(u"First name"),
                                     missing = u"")
    last_name = colander.SchemaNode(colander.String(),
                                    title = _(u"Last name"),
                                    missing = u"")
    password = colander.SchemaNode(colander.String(),
                                   title = _(u"Password"),
                                   validator = colander.Length(min = 6, max = 200),
                                   widget = deform.widget.CheckedPasswordWidget(redisplay = True))


class CombinedRegistrationSchema(FinishRegistrationSchema, RegistrationSchema):
    """ For when email isn't validated. """


class RecoverPasswordSchema(colander.Schema):
    email_or_userid = colander.SchemaNode(colander.String(),
                                          preparer = to_lowercase,
                                          validator = existing_userid_or_email,
                                          title = _(u"Email or UserID"),)


class RootSchema(BaseSchema, DCMetadataSchema):
    head_title = colander.SchemaNode(colander.String(),
        title = _("Page head title"),
        description = _("Usually shown as a title of the browser tab."),)
    footer = colander.SchemaNode(colander.String(),
        title = _("Footer"),
        missing = "",
        widget = deform.widget.RichTextWidget(delayed_load = True, height = 200))


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
    show_login_link = colander.SchemaNode(colander.Bool(),
                                          title = _("Show login link."),
                                          default = True)
    skip_email_validation = colander.SchemaNode(colander.Bool(),
                                                title = _("Skip email validation"),
                                                description = _("This will allow users to register with a fake email address. Generally not recommended."))


def includeme(config):
    config.add_content_schema('Document', DocumentSchema, ('view', 'edit', 'add'))
    config.add_content_schema('User', UserSchema, ('view', 'edit'))
    config.add_content_schema('User', AddUserSchema, 'add')
    config.add_content_schema('User', ChangePasswordSchema, 'change_password')
    config.add_content_schema('InitialSetup', InitialSetup, 'setup')
    config.add_content_schema('Auth', LoginSchema, 'login')
    config.add_content_schema('Auth', RegistrationSchema, 'register')
    config.add_content_schema('Auth', FinishRegistrationSchema, 'register_finish')
    config.add_content_schema('Auth', CombinedRegistrationSchema, 'register_skip_validation')
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
