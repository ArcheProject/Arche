from datetime import datetime

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
        if request is None:
            request = get_current_request()
        self.request = request
        if tz_name is None:
            tz_name = request.registry.settings.get('arche.timezone', 'UTC')
        try:
            self.timezone = pytz.timezone(tz_name)
        except pytz.UnknownTimeZoneError:
            self.timezone = pytz.timezone('UTC')
        if locale is None:
            locale = request.locale_name
        self.locale = locale

    def normalize(self, value):
        return self.timezone.normalize(value.astimezone(self.timezone))

    def format_dt(self, value, format='short', parts = 'dt', localtime = True):
        if localtime:
            dt = self.normalize(value)
        else:
            dt = value
        if parts == 'd':
            return format_date(dt, format = format, locale = self.locale)
        if parts == 't':
            return format_time(dt, format = format, locale = self.locale)
        return format_datetime(dt, format = format, locale = self.locale)

    def string_convert_dt(self, value, pattern = "%Y-%m-%dT%H:%M:%S"):
        """ Convert a string to a localized datetime. """
        return self.timezone.localize(datetime.strptime(value, pattern))

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
        #Check if timezone is naive, convert
        if value.tzinfo is None:
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
                return _("${diff} minutes ago", mapping={'diff': str(second_diff / 60)})
            if second_diff < 7200:
                return _("1 hour ago")
            if second_diff < 86400:
                return _("${diff} hours ago", mapping={'diff': str(second_diff / 3600)})
        return self.format_dt(value)

def includeme(config):
    config.registry.registerAdapter(DateTimeHandler)
