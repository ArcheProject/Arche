from datetime import datetime, date

from babel.dates import format_date
from babel.dates import format_datetime
from babel.dates import format_time
from pyramid.interfaces import IRequest
from pyramid.threadlocal import get_current_request
from zope.component import adapter
from zope.interface import implementer
import pytz

from arche import _
from arche.interfaces import IDateTimeHandler
from arche.utils import utcnow


@implementer(IDateTimeHandler)
@adapter(IRequest)
class DateTimeHandler(object):
    """ Handle conversion and printing of date and time.
    """
    locale = None
    timezone = None

    def __init__(self, request = None, tz_name = None, locale = None):
        """ The keyword arguments are mostly ment for tests.
            Normally this method is accessed as an attribute
            of the request object it wraps.
        """
        if request is None:
            request = get_current_request()
        self.request = request
        self.timezone = self.get_timezone(tz_name = tz_name)
        if locale is None:
            locale = request.locale_name
        self.locale = locale

    def get_timezone(self, tz_name = None):
        try:
            return self.request.session['__timezone__']
        except KeyError:
            if tz_name is None:
                tz_name = self.get_tzname()
            self.request.session['__timezone__'] = tz = pytz.timezone(tz_name)
            return tz

    def get_tzname(self):
        """ Fetch timezone from user profile, default settings or simply set utc. """
        if self.request.authenticated_userid:
            user = self.request.root['users']. get(self.request.authenticated_userid)
            tz_name = getattr(user, 'timezone', None)
            if tz_name != None:
                return tz_name
        return self.get_default_tzname()

    def get_default_tzname(self):
        return self.request.registry.settings.get('arche.timezone', 'UTC')

    def reset_timezone(self):
        self.request.session.pop('__timezone__', None)
        self.timezone = self.get_timezone()

    def format_dt(self, value, format='short', parts = 'dt', localtime = True):
        if localtime and isinstance(value, datetime):
            try:
                dt = value.astimezone(self.timezone)
            except ValueError: #Is this a safe assumption? To die on naive dt is silly too.
                dt = value
        else:
            dt = value
        if parts == 'd':
            return format_date(dt, format = format, locale = self.locale)
        if parts == 't':
            return format_time(dt, format = format, locale = self.locale)
        return format_datetime(dt, format = format, locale = self.locale)

    def utcnow(self):
        return utcnow()

    def localnow(self):
        return datetime.now(self.timezone)

    def tz_to_utc(self, value):
        return value.astimezone(pytz.utc)

    def format_relative(self, value):
        """ Get a datetime object or a int() Epoch timestamp and return a
            pretty string like 'an hour ago', 'Yesterday', '3 months ago',
            'just now', etc
        """
        if isinstance(value, int):
            value = datetime.fromtimestamp(value, pytz.utc)
        if type(value) == date: #datetime subclasses date
            return format_date(value, format = 'short', locale = self.locale)
        #Check if timezone is naive, convert
        if isinstance(value, datetime) and value.tzinfo is None:
            raise ValueError("Not possible to use format_relative with timezone naive datetimes.")
        elif value.tzinfo is not pytz.utc:
            value = self.tz_to_utc(value)

        now = self.utcnow()
        diff = now - value
        second_diff = diff.seconds
        day_diff = diff.days

        if day_diff < 0:
            #FIXME: Shouldn't future be handled as well? :)
            return self.format_dt(value)

        if day_diff == 0:
            if second_diff < 10:
                return _("Just now")
            if second_diff < 60:
                return _("${diff} seconds ago", mapping={'diff': str(second_diff)})
            if second_diff < 120:
                return  _("1 minute ago")
            if second_diff < 3600:
                return _("${diff} minutes ago", mapping={'diff': str(second_diff // 60)})
            if second_diff < 7200:
                return _("1 hour ago")
            if second_diff < 86400:
                return _("${diff} hours ago", mapping={'diff': str(second_diff // 3600)})
        return self.format_dt(value)

def includeme(config):
    config.registry.registerAdapter(DateTimeHandler)
