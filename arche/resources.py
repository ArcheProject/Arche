from __future__ import unicode_literals
from datetime import timedelta
from random import choice
from uuid import uuid4
import string

from BTrees.OOBTree import OOBTree
from BTrees.OOBTree import OOSet
from colander import null
from persistent import Persistent
from persistent.list import PersistentList
from pyramid.threadlocal import get_current_registry
from pyramid.threadlocal import get_current_request
from pyramid.traversal import find_resource
from repoze.folder import Folder
from six import string_types
from zope.component.event import objectEventNotify
from zope.interface import implementer

from arche import _
from arche.models.catalog import create_catalog
from arche.events import EmailValidatedEvent
from arche.events import ObjectUpdatedEvent
from arche.interfaces import (IBase,
                              IBlobs,
                              IContent,
                              IContextACL,
                              IDocument,
                              IFile,
                              IGroup,
                              IGroups,
                              IImage,
                              IIndexedContent,
                              IInitialSetup,
                              ILink,
                              ILocalRoles,
                              IObjectAddedEvent,
                              IRoles,
                              IRoot,
                              IThumbnailedContent,
                              IToken,
                              ITrackRevisions,
                              IUser,
                              IUsers)
from arche.security import (ROLE_OWNER,
                            get_acl_registry)
from arche import security

from arche.utils import (hash_method,
                         utcnow)
from arche.models.workflow import get_context_wf
from arche.interfaces import ICataloger


class DCMetadataMixin(object):
    """ Dublin Core metadata"""
    title = u""
    description = u""
    created = None #FIXME
    modified = None #FIXME - also via update?
    date = None
    publisher = u""
    subject = u"" #FIXME: Same as tags?
    relation = u"" #Probably a  relation field here
    rights = u"" #FIXME: global default is a good idea
    
    #type = u"" #FIXME?
    format = u"" #Mimetype or similar?
    source = u"" #Sources?
    #identifier (Something like current url?)

    @property
    def contributor(self): return getattr(self, '__contributor__', ())
    @contributor.setter
    def contributor(self, value):
        if value:
            self.__contributor__ = PersistentList(value)
        else:
            if hasattr(self, '__contributor__'):
                delattr(self, '__contributor__')

    @property
    def creator(self): return getattr(self, '__creator__', ())
    @creator.setter
    def creator(self, value):
        if value:
            self.__creator__ = PersistentList(value)
        else:
            if hasattr(self, '__creator__'):
                delattr(self, '__creator__')

    @property
    def relation(self):
        return getattr(self, '__relation__', ())
    
    @relation.setter
    def relation(self, value):
        if value:
            self.__relation__ = PersistentList(value)
        else:
            if hasattr(self, '__relation__'):
                delattr(self, '__relation__')


@implementer(IBase)
class BaseMixin(object):
    type_name = ""
    type_title = ""
    type_description = ""
    uid = None
    created = ""
    nav_visible = False
    listing_visible = True
    search_visible = False
    show_byline = False
    naming_attr = 'title'

    def __init__(self, **kwargs):
        #IContent should be the same iface registered by the roles adapter
        if 'local_roles' not in kwargs and ILocalRoles.providedBy(self):
            request = get_current_request()
            #Check creators attribute?
            userid = getattr(request, 'authenticated_userid', None)
            if userid:
                kwargs['local_roles'] = {userid: [ROLE_OWNER]}
        if 'uid' not in kwargs:
            kwargs['uid'] = unicode(uuid4())
        if 'created' not in kwargs and hasattr(self, 'created'):
            kwargs['created'] = utcnow()
        if 'data' in kwargs: #Shouldn't be set here. Create a proper blocklist?
            del kwargs['data']
        self.update(event = False, **kwargs)

    def update(self, event = True, **kwargs):
        _marker = object()
        changed_attributes = set()
        for (key, value) in kwargs.items():
            if not hasattr(self, key):
                raise AttributeError("%r doesn't have any '%s' attribute." % (self, key))
            if value == null:
                value = None
            if getattr(self, key, _marker) != value:
                setattr(self, key, value)
                changed_attributes.add(key)
        if hasattr(self, 'modified') and 'modified' not in kwargs and changed_attributes:
            self.modified = utcnow()
            changed_attributes.add('modified')
        if event:
            event_obj = ObjectUpdatedEvent(self, changed = changed_attributes)
            objectEventNotify(event_obj)
        return changed_attributes


class Base(Persistent, BaseMixin):
    __name__ = None
    __parent__ = None

    def __init__(self, **kw):
        super(Base, self).__init__()
        BaseMixin.__init__(self, **kw)

    def __repr__(self): #pragma: no coverage
        klass = self.__class__
        classname = '%s.%s' % (klass.__module__, klass.__name__)
        return '<%s object %r at %#x>' % (classname,
                                          self.__name__,
                                          id(self))


@implementer(ILocalRoles)
class LocalRolesMixin(object):

    @property
    def local_roles(self): return IRoles(self)

    @local_roles.setter
    def local_roles(self, value):
        #Note that you can also set roles via the property, like self.local_roles['admin'] = ['role:Admin']
        local_roles = IRoles(self)
        local_roles.set_from_appstruct(value)


@implementer(IContextACL)
class ContextACLMixin(object):
    """ Mixin for content that cares about security in some way. Could either be workflows or ACL."""

    @property
    def __acl__(self):
        acl_reg = get_acl_registry()
        wf = self.workflow
        if wf:
            state = wf.state in wf.states and wf.state or wf.initial_state
            return acl_reg.get_acl("%s:%s" % (wf.name, state))
        elif self.type_name in acl_reg:
            return acl_reg.get_acl(self.type_name)
        return acl_reg.get_acl('default')

    @property
    def workflow(self):
        return get_context_wf(self)

    @property
    def wf_state(self):
        wf = self.workflow
        if wf:
            return wf.state in wf.states and wf.state or wf.initial_state


@implementer(IContent, IIndexedContent, ITrackRevisions)
class Content(Base, Folder):
    title = ""
    description = ""
    default_view = u"view"
    delegate_view = None
    nav_visible = True
    nav_title = None
    listing_visible = True
    search_visible = True
    show_byline = False

    def __init__(self, **kw):
        Folder.__init__(self)
        super(Content, self).__init__(**kw)

    def get_nav_title(self):
        nav_title = getattr(self, 'nav_title', None)
        return nav_title and nav_title or self.title

    @property
    def tags(self): return getattr(self, '__tags__', ())
    @tags.setter
    def tags(self, value):
        #Is this the right way to mutate objects, or should we simply clear the contents?
        if value:
            self.__tags__ = OOSet(value)
        else:
            if hasattr(self, '__tags__'):
                delattr(self, '__tags__')


@implementer(ILink)
class Link(Content):
    """ A persistent way of redirecting somewhere. """
    type_name = u"Link"
    type_title = _(u"Link")
    type_description = _(u"Content type that redirects to somewhere.")
    add_permission = "Add %s" % type_name
    target = u""
    css_icon = "glyphicon glyphicon-link"
    nav_visible = False
    listing_visible = False
    search_visible = False

external_type_icons = {'photo': 'picture',
                       'video': 'film',
                       'rich': 'cloud'}
#Set this via subscriber? Propbably


@implementer(IRoot, IIndexedContent)
class Root(Content, LocalRolesMixin, DCMetadataMixin, ContextACLMixin):
    type_name = u"Root"
    type_title = _(u"Site root")
    add_permission = "Add %s" % type_name
    search_visible = False
    is_permanent = True
    footer = ""
    head_title = "Arche"

    def __init__(self, data=None, **kwargs):
        create_catalog(self)
        super(Root, self).__init__(data=data, **kwargs)
        cataloger = ICataloger(self, None)
        if cataloger:
            cataloger.index_object()

    @property
    def allow_self_registration(self):
        """ This might change to an actual setting later. """
        return self.site_settings.get('allow_self_registration', False)

    @property
    def skip_email_validation(self):
        return self.site_settings.get('skip_email_validation', False)

    @property
    def __acl__(self):
        acl_entries = []
        if self.allow_self_registration:
            acl_entries.append((security.Allow, security.Everyone, security.PERM_REGISTER))
        acl_reg = get_acl_registry()
        wf = get_context_wf(self)
        if wf:
            state = wf.state in wf.states and wf.state or wf.initial_state
            acl_entries.extend(acl_reg.get_acl("%s:%s" % (wf.name, state)))
        elif self.type_name in acl_reg:
            acl_entries.extend( acl_reg.get_acl(self.type_name) )
        else:
            acl_entries.append(security.DENY_ALL)
        return acl_entries

    @property
    def site_settings(self): return getattr(self, '__site_settings__', {})
    @site_settings.setter
    def site_settings(self, value):
        self.__site_settings__ = OOBTree(value)


@implementer(IDocument, IThumbnailedContent)
class Document(Content, DCMetadataMixin, LocalRolesMixin, ContextACLMixin):
    type_name = u"Document"
    type_title = _(u"Document")
    body = ""
    add_permission = "Add %s" % type_name
    css_icon = "glyphicon glyphicon-font"

    @property
    def image_data(self):
        blobs = IBlobs(self, None)
        if blobs:
            return blobs.formdata_dict('image')
    @image_data.setter
    def image_data(self, value):
        IBlobs(self).create_from_formdata('image', value)


@implementer(IFile, IThumbnailedContent)
class File(Content, DCMetadataMixin):
    type_name = "File"
    type_title = _("File")
    add_permission = "Add %s" % type_name
    blob_key = "file"
    filename = ""
    mimetype = ""
    css_icon = "glyphicon glyphicon-file"

    def __init__(self, file_data, **kwargs):
        self._title = u""
        super(File, self).__init__(file_data = file_data, **kwargs)

    @property
    def title(self):
        return self._title and self._title or self.filename
    @title.setter
    def title(self, value): self._title = value

    @property
    def file_data(self):
        blobs = IBlobs(self, None)
        if blobs:
            return blobs.formdata_dict(self.blob_key)
    @file_data.setter
    def file_data(self, value):
        blob_file = IBlobs(self).create_from_formdata(self.blob_key, value)
        if blob_file:
            self.filename = blob_file.filename
            self.mimetype = blob_file.mimetype
            #Settable types?
            styles = {'video': 'glyphicon glyphicon-film',
                      'image': 'glyphicon glyphicon-picture'}
            main = self.mimetype.split('/')[0]
            new_icon_css = styles.get(main, None)
            if new_icon_css:
                self.css_icon = new_icon_css

    @property
    def size(self):
        blobs = IBlobs(self)
        return self.blob_key in blobs and blobs[self.blob_key].size or u""


@implementer(IImage)
class Image(File, DCMetadataMixin):
    type_name = "Image"
    type_title = _("Image")
    add_permission = "Add %s" % type_name
    blob_key = "file"
    css_icon = "glyphicon glyphicon-picture"


@implementer(IInitialSetup)
class InitialSetup(Content):
    type_name = "InitialSetup"
    type_title = _("Initial setup")
    nav_visible = False
    search_visible = False
    title = _("Welcome to Arche!")
    setup_data = {}
    add_permission = None
    head_title = _("Initial Setup")


@implementer(IUsers)
class Users(Content, LocalRolesMixin, ContextACLMixin):
    type_name = u"Users"
    type_title = _(u"Users")
    nav_visible = False
    listing_visible = False
    search_visible = False
    title = _(u"Users")
    is_permanent = True
    add_permission = None

    def get_user_by_email(self, email, default = None, only_validated = False):
        """ Get a user object by email address regardless of permissions.
            Used by validators, login etc.
        """
        root = self.__parent__
        email = email.lower()
        res, docids = root.catalog.query("type_name == 'User' and email == '%s'" % email)
        if res.total > 1:
            raise ValueError("Catalog query for %r returned more than one user with the same email address." % email)
        if res.total == 0:
            return default
        docid = tuple(docids)[0]
        path = root.document_map.address_for_docid(docid)
        user = find_resource(root, path)
        if only_validated and user.email_validated == False:
            return default
        return user

    def get_user(self, value, default = None, only_validated = False):
        """ Fetch a user by either email or userid.
        """
        value = value.lower()
        if '@' in value:
            return self.get_user_by_email(value, default = default, only_validated = only_validated)
        return self.get(value, default)


@implementer(IUser, IThumbnailedContent, IContent)
class User(Content, LocalRolesMixin, ContextACLMixin):
    type_name = u"User"
    type_title = _(u"User")
    first_name = u""
    last_name = u""
    email = u""
    add_permission = "Add %s" % type_name
    pw_token = None
    css_icon = "glyphicon glyphicon-user"
    allow_login = True
    _email_validated = False
    __timezone__ = None

    @property
    def title(self):
        title = " ".join((self.first_name, self.last_name,)).strip()
        return title and title or self.userid

    @property
    def userid(self): return self.__name__

    @property
    def password(self): return getattr(self, "__password_hash__", u"")
    @password.setter
    def password(self, value):
        if value:
            self.__password_hash__ = hash_method(value)
        else:
            self.__password_hash__ = None

    @property
    def email_validated(self): return getattr(self, "_email_validated", False)
    @email_validated.setter
    def email_validated(self, value):
        """ Set email as validated. If the object is attached to the resource tree
            and the value was changed from False to True, send event.
            Also, attaching this object to the resource tree will send the event
            if email_validated is True.
        """
        if value == True:
            if self._email_validated != True:
                self._email_validated = True
                if self.__parent__ != None:
                    reg = get_current_registry()
                    reg.notify(EmailValidatedEvent(self))
        else:
            self._email_validated = False

    @property
    def image_data(self):
        blobs = IBlobs(self, None)
        if blobs:
            return blobs.formdata_dict('image')
    @image_data.setter
    def image_data(self, value):
        IBlobs(self).create_from_formdata('image', value)

    @property
    def timezone(self):
        return getattr(self, '__timezone__', None)
    @timezone.setter
    def timezone(self, value):
        if value:
            assert isinstance(value, string_types), "Must be a string"
            setattr(self, '__timezone__', value)
        else:
            setattr(self, '__timezone__', None)
        #Invalidate tz cache
        req = get_current_request()
        req.dt_handler.reset_timezone()


@implementer(IGroups)
class Groups(Content, LocalRolesMixin, ContextACLMixin):
    type_name = u"Groups"
    type_title = _(u"Groups")
    nav_visible = False
    listing_visible = False
    search_visible = False
    title = _(u"Groups")
    is_permanent = True
    add_permission = "Add %s" % type_name

    def get_users_group_principals(self, userid):
        #Cache memberships? Needed on sites with many groups
        groups = set()
        for group in self.values():
            if userid in group.members:
                groups.add(group.principal_name)
        return groups

    def get_group_principals(self):
        for group in self.values():
            yield group.principal_name


@implementer(IGroup)
class Group(Content, LocalRolesMixin, ContextACLMixin):
    type_name = u"Group"
    type_title = _(u"Group")
    add_permission = "Add %s" % type_name
    title = u""
    description = u""
    css_icon = "glyphicon glyphicon-user" #FIXME no group icon!?

    def __init__(self, **kwargs):
        #Things like created, creator etc...
        super(Group, self).__init__()
        self.__members__ = OOSet()
        self.update(event = False, **kwargs)

    @property
    def principal_name(self):
        """ The way the security system likes to check names
            to avoid collisions with userids.
        """
        return u"group:%s" % self.__name__

    @property
    def members(self):
        return self.__members__

    @members.setter
    def members(self, value):
        self.__members__.clear()
        self.__members__.update(value)


@implementer(IToken)
class Token(Persistent):
    created = None
    expires = None
    type_name = u"Token"
    type_tile = _(u"Token")
    add_permission = "Add %s" % type_name

    def __init__(self, size = 40, hours = 3):
        self.token = ''.join([choice(string.letters + string.digits) for x in range(size)])
        self.created = utcnow()
        if hours:
            self.expires = self.created + timedelta(hours = hours)

    def __str__(self): return str(self.token)
    def __repr__(self): return repr(self.token)
    def __cmp__(self, txt): return cmp(self.token, txt)

    @property
    def valid(self):
        if self.expires is None:
            return True
        return self.expires > utcnow()


def make_user_owner(user, event = None):
    """ Whenever a user object is added, make sure the user has the role owner,
        and no one else. This might not be the default behaviour, if an
        administrator adds the user.
    """
    if ROLE_OWNER not in user.local_roles.get(user.userid, ()):
        user.local_roles = {user.userid: [ROLE_OWNER]}


def includeme(config):
    config.add_content_factory(Document)
    config.add_addable_content('Document', ('Document', 'Root'))
    config.add_content_factory(Users)
    config.add_content_factory(User)
    config.add_addable_content('User', 'Users')
    config.add_content_factory(InitialSetup)
    config.add_content_factory(Groups)
    config.add_content_factory(Group)
    config.add_addable_content('Group', 'Groups')
    config.add_content_factory(File)
    config.add_addable_content('File', ('Root', 'Document'))
    config.add_content_factory(Image)
    config.add_addable_content('Image', ('Root', 'Document'))
    config.add_content_factory(Root)
    config.add_content_factory(Link)
    config.add_addable_content('Link', ('Root', 'Document'))
    config.add_content_factory(Token)
    config.add_subscriber(make_user_owner, [IUser, IObjectAddedEvent])
