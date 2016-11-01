""" Python 2/3 compat
"""

try:
    from UserDict import IterableUserDict
    from UserString import UserString
    from urllib import unquote
except ImportError:
    from collections import UserDict as IterableUserDict
    from collections import UserString
    from urllib.parse import unquote
