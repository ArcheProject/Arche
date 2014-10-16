import datetime

from pyramid.threadlocal import get_current_request
import colander
import deform

from arche import _
from arche.interfaces import IPopulator
from arche.security import get_roles_registry
from arche.utils import FileUploadTempStore
from arche.validators import existing_userid_or_email
from arche.validators import login_password_validator
from arche.validators import unique_email_validator
from arche.validators import unique_userid_validator
from arche.widgets import DropzoneWidget
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
def global_roles_widget(node, kw):
    request = kw['request']
    rr = get_roles_registry(request.registry)
    values = [(role, role.title) for role in rr.assign_global()]
    return deform.widget.CheckboxChoiceWidget(values = values, inline = True)

@colander.deferred
def principal_hinter_widget(node, kw):
    view = kw['view']
    values = set(view.root['users'].keys())
    values.update(view.root['groups'].get_group_principals())
    return deform.widget.AutocompleteInputWidget(values = tuple(values))

@colander.deferred
def userid_hinder_widget(node, kw):
    view = kw['view']
    return deform.widget.AutocompleteInputWidget(values = tuple(view.root['users'].keys()))

@colander.deferred
def file_upload_widget(node, kw):
    request = kw['request']
    tmpstorage = FileUploadTempStore(request)
    return DropzoneWidget(tmpstorage, template='arche:templates/deform/widgets/dropzone.pt')

@colander.deferred
def populators_choice(node, kw):
    request = kw['request']
    values = [('', _('No thanks'))]
    values.extend([(x.name, x.name) for x in request.registry.registeredAdapters() if x.provided == IPopulator])
    return deform.widget.SelectWidget(values = values)

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
    creator = colander.SchemaNode(colander.List(),
                                  tab = 'metadata',
                                  widget = ReferenceWidget(query_params = {'type_name': 'User'}),
                                  missing = colander.null,
                                  default = current_users_uid)
    contributor = colander.SchemaNode(colander.List(),
                                      widget = ReferenceWidget(query_params = {'type_name': 'User'}),
                                      tab = 'metadata',
                                      missing = colander.null)
    created = colander.SchemaNode(DateTime(),
                                  default = default_now,
                                  missing = colander.null,
                                  tab = 'metadata')
    relation = colander.SchemaNode(colander.List(),
                                   title = _(u"Related content"),
                                   description = _(u"Can be used to link to other content"),
                                   tab = 'metadata',
                                   missing = colander.null,
                                   widget = ReferenceWidget())
    publisher = colander.SchemaNode(colander.String(),
                                    missing = colander.null,
                                  tab = 'metadata')
    date = colander.SchemaNode(DateTime(),
                               title = _(u"Date"),
                               description = _(u"Publish date, or used for sorting"),
                               default = default_now,
                               missing = colander.null,
                               tab = 'metadata')
    subject = colander.SchemaNode(colander.String(),
                                  title = _(u"Tags or subjects"),
                                  missing = u"",
                                  tab = 'metadata')
    rights = colander.SchemaNode(colander.String(),
                                 title = _(u"Licensing"),
                                 missing = u"",
                                 tab = 'metadata')
    tags = colander.SchemaNode(colander.List(),
                               title = _("Tags"),
                               missing = "",
                               widget = tagging_widget)
    #type?
    #format
    #identifier -> url
    #source
    #language


class BaseSchema(colander.Schema):
    nav_visible = colander.SchemaNode(colander.Bool(),
                                      title = _(u"Show in navigations"),
                                      missing = colander.null,
                                      default = True,
                                      tab = tabs['visibility'])
    listing_visible = colander.SchemaNode(colander.Bool(),
                                          title = _(u"Show in listing or table views"),
                                          description = _(u"The content view will always show this regardless of what you set."),
                                          missing = colander.null,
                                          default = True,
                                          tab = tabs['visibility'])
    search_visible = colander.SchemaNode(colander.Bool(),
                                         title = _(u"Include in search results"),
                                         description = _(u"Note that this is not a permission setting - it's just a matter of practicality for users. "
                                                         u"They may even disable this setting."),
                                         missing = colander.null,
                                         default = True,
                                         tab = tabs['visibility'])


class DocumentSchema(BaseSchema, DCMetadataSchema):
    body = colander.SchemaNode(colander.String(),
                               widget = deform.widget.RichTextWidget(),
                               missing = u"")
    image_data = colander.SchemaNode(deform.FileData(),
                                         missing = None,
                                         title = _(u"Image"),
                                         widget = file_upload_widget)
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
                                       title = _(u"Replace profile image"),
                                       widget = file_upload_widget)
    

class AddUserSchema(UserSchema):
    userid = colander.SchemaNode(colander.String(),
                                 validator = unique_userid_validator)
    password = colander.SchemaNode(colander.String(),
                                   title = _(u"Password"),
                                   widget = deform.widget.CheckedPasswordWidget())
    image_data = colander.SchemaNode(deform.FileData(),
                                       missing = colander.null,
                                       title = _(u"Add profile image"),
                                       widget = file_upload_widget)


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
    pass


def permissions_schema_factory(context, request, view):
    rr = get_roles_registry(request.registry)
    values = [(role, role.title) for role in rr.assign_local()]
    roles_widget = deform.widget.CheckboxChoiceWidget(values = values,
                                                      inline = True)
    schema = colander.Schema()
    for user in view.root['users'].values():
        schema.add(colander.SchemaNode(
            colander.Set(),
            tab = 'users',
            name = user.userid,
            title = user.title,
            widget = roles_widget,)
        )
    for group in view.root['groups'].values():
        schema.add(colander.SchemaNode(
            colander.Set(),
            tab = 'groups',
            name = group.principal_name,
            title = group.title,
            description = group.description,
            widget = roles_widget,)
        )
    return schema


class AddFileSchema(BaseSchema, DCMetadataSchema):
    title = colander.SchemaNode(colander.String(),
                                missing = u"")
    file_data = colander.SchemaNode(deform.FileData(),
                                    title = _(u"Upload file"),
                                    widget = file_upload_widget)


class EditFileSchema(AddFileSchema, DCMetadataSchema):
    file_data = colander.SchemaNode(deform.FileData(),
                                    title = _(u"Replace file"),
                                    missing = colander.null,
                                    widget = file_upload_widget)


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
    config.add_content_schema('Document', DocumentSchema, 'view')
    config.add_content_schema('Document', DocumentSchema, 'edit')
    config.add_content_schema('Document', DocumentSchema, 'add')
    config.add_content_schema('User', UserSchema, 'view')
    config.add_content_schema('User', UserSchema, 'edit')
    config.add_content_schema('User', AddUserSchema, 'add')
    config.add_content_schema('User', ChangePasswordSchema, 'change_password')
    config.add_content_schema('InitialSetup', InitialSetup, 'setup')
    config.add_content_schema('Auth', LoginSchema, 'login')
    config.add_content_schema('Auth', RegistrationSchema, 'register')
    config.add_content_schema('Auth', FinishRegistrationSchema, 'register_finish')
    config.add_content_schema('Auth', RecoverPasswordSchema, 'recover_password')
    config.add_content_schema('Group', GroupSchema, 'add')
    config.add_content_schema('Group', GroupSchema, 'view')
    config.add_content_schema('Group', GroupSchema, 'edit')
    config.add_content_schema('File', AddFileSchema, 'add')
    config.add_content_schema('File', EditFileSchema, 'edit')
    config.add_content_schema('Image', AddFileSchema, 'add') #Specific schema?
    config.add_content_schema('Image', EditFileSchema, 'edit')
    config.add_content_schema('Root', RootSchema, 'edit')
    config.add_content_schema('Root', SiteSettingsSchema, 'site_settings')
    config.add_content_schema('Link', AddLinkSchema, 'add')
    config.add_content_schema('Link', LinkSchema, 'edit')
