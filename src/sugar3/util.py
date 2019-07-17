"""Various utility functions"""
# Copyright (C) 2006-2007 Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""
UNSTABLE. We have been adding helpers randomly to this module.
"""

import six
import os
import time
import hashlib
import random
import binascii
import gettext
import tempfile
import logging
import atexit


def _(msg):
    return gettext.dgettext('sugar-toolkit-gtk3', msg)


def printable_hash(in_hash):
    """Convert binary hash data into printable characters."""
    printable = ""
    for char in in_hash:
        if six.PY3:
            char = bytes([char])
            printable = printable + binascii.b2a_hex(char).decode()
        else:
            printable = printable + binascii.b2a_hex(char)
    return printable


def sha_data(data):
    """sha1 hash some bytes."""
    sha_hash = hashlib.sha1()
    if six.PY3:
        data = data.encode('utf-8')
    sha_hash.update(data)
    return sha_hash.digest()


def unique_id(data=''):
    """Generate a likely-unique ID for whatever purpose

    data -- suffix appended to working data before hashing

    Returns a 40-character string with hexidecimal digits
    representing an SHA hash of the time, a random digit
    within a constrained range and the data passed.

    Note: these are *not* crypotographically secure or
        globally unique identifiers.  While they are likely
        to be unique-enough, no attempt is made to make
        perfectly unique values.
    """
    data_string = '%s%s%s' % (time.time(), random.randint(10000, 100000), data)
    return printable_hash(sha_data(data_string))


ACTIVITY_ID_LEN = 40


def is_hex(s):
    try:
        int(s, 16)
    except ValueError:
        return False

    return True


def validate_activity_id(actid):
    """Validate an activity ID."""
    if not isinstance(actid, (six.binary_type, six.text_type)):
        return False
    if len(actid) != ACTIVITY_ID_LEN:
        return False
    if not is_hex(actid):
        return False
    return True


def set_proc_title(title):
    """Sets the process title so ps and top show more
       descriptive names.  This does not modify argv[0]
       and only the first 15 characters will be shown.

       title -- the title you wish to change the process
                title to

       Returns True on success.  We don't raise exceptions
       because if something goes wrong here it is not a big
       deal as this is intended as a nice thing to have for
       debugging
    """
    try:
        import ctypes
        libc = ctypes.CDLL('libc.so.6')
        libc.prctl(15, str(title), 0, 0, 0)

        return True
    except Exception:
        return False


class Node(object):

    __slots__ = ['prev', 'next', 'me']

    def __init__(self, prev, me):
        self.prev = prev
        self.me = me
        self.next = None


class LRU:
    """
    Implementation of a length-limited O(1) LRU queue.
    Built for and used by PyPE:
    http://pype.sourceforge.net
    Copyright 2003 Josiah Carlson.
    """

    def __init__(self, count, pairs=[]):
        # pylint: disable=W0102,W0612
        self.count = max(count, 1)
        self.d = {}
        self.first = None
        self.last = None
        for key, value in pairs:
            self[key] = value

    def __contains__(self, obj):
        return obj in self.d

    def __getitem__(self, obj):
        a = self.d[obj].me
        self[a[0]] = a[1]
        return a[1]

    def __setitem__(self, obj, val):
        if obj in self.d:
            del self[obj]
        nobj = Node(self.last, (obj, val))
        if self.first is None:
            self.first = nobj
        if self.last:
            self.last.next = nobj
        self.last = nobj
        self.d[obj] = nobj
        if len(self.d) > self.count:
            if self.first == self.last:
                self.first = None
                self.last = None
                return
            a = self.first
            a.next.prev = None
            self.first = a.next
            a.next = None
            del self.d[a.me[0]]
            del a

    def __delitem__(self, obj):
        nobj = self.d[obj]
        if nobj.prev:
            nobj.prev.next = nobj.next
        else:
            self.first = nobj.next
        if nobj.next:
            nobj.next.prev = nobj.prev
        else:
            self.last = nobj.prev
        del self.d[obj]

    def __iter__(self):
        cur = self.first
        while cur is not None:
            cur2 = cur.next
            yield cur.me[1]
            cur = cur2

    def iteritems(self):
        cur = self.first
        while cur is not None:
            cur2 = cur.next
            yield cur.me
            cur = cur2

    def iterkeys(self):
        return iter(self.d)

    def itervalues(self):
        for i_, j in six.iteritems(self):
            yield j

    def keys(self):
        return list(self.d.keys())


units = [['%d year', '%d years', 356 * 24 * 60 * 60],
         ['%d month', '%d months', 30 * 24 * 60 * 60],
         ['%d week', '%d weeks', 7 * 24 * 60 * 60],
         ['%d day', '%d days', 24 * 60 * 60],
         ['%d hour', '%d hours', 60 * 60],
         ['%d minute', '%d minutes', 60]]

AND = _(' and ')
COMMA = _(', ')

# TRANS: Indicating something that just happened, eg. "just now", "moments ago"
NOW = _('Seconds ago')

# TRANS: Indicating time passed, eg. "[10 day, 5 hours] ago",
# "[2 minutes] in the past", or "[3 years, 1 month] earlier"
ELAPSED = _('%s ago')

# Explanation of the following hack:
# The xgettext utility extracts plural forms by reading the strings included as
# parameters of ngettext(). As our plurals are not passed to ngettext()
# straight away because there needs to be a calculation before we know which
# strings need to be used, then we need to call ngettext() in a fake way so
# xgettext will pick them up as plurals.


def ngettext(singular, plural, n):
    pass


# TRANS: Relative dates (eg. 1 month and 5 days).
ngettext('%d year', '%d years', 1)
ngettext('%d month', '%d months', 1)
ngettext('%d week', '%d weeks', 1)
ngettext('%d day', '%d days', 1)
ngettext('%d hour', '%d hours', 1)
ngettext('%d minute', '%d minutes', 1)

del ngettext

# End of plurals hack


# gettext perfs hack (#7959)
_i18n_timestamps_cache = LRU(60)


def timestamp_to_elapsed_string(timestamp, max_levels=2):
    levels = 0
    time_period = ''
    elapsed_seconds = int(time.time() - timestamp)

    for name_singular, name_plural, factor in units:
        elapsed_units = int(elapsed_seconds / factor)
        if elapsed_units > 0:

            if levels > 0:
                time_period += COMMA

            key = ''.join((os.environ['LANG'], name_singular,
                           str(elapsed_units)))
            if key in _i18n_timestamps_cache:
                time_period += _i18n_timestamps_cache[key]
            else:
                tmp = gettext.dngettext('sugar-toolkit-gtk3',
                                        name_singular,
                                        name_plural,
                                        elapsed_units)
                # FIXME: This is a hack so we don't crash when a translation
                # doesn't contain the expected number of placeholders (#2354)
                try:
                    translation = tmp % elapsed_units
                except TypeError:
                    translation = tmp

                _i18n_timestamps_cache[key] = translation
                time_period += translation

            elapsed_seconds -= elapsed_units * factor

        if time_period != '':
            levels += 1

        if levels == max_levels:
            break

    if levels == 0:
        return NOW

    return ELAPSED % time_period


_tracked_paths = {}


class TempFilePath(str):

    def __new__(cls, path=None):
        if path is None:
            fd, path = tempfile.mkstemp()
            os.close(fd)
        logging.debug('TempFilePath created %r' % path)

        if path in _tracked_paths:
            _tracked_paths[path] += 1
        else:
            _tracked_paths[path] = 1

        return str.__new__(cls, path)

    def __del__(self):
        if _tracked_paths[self] == 1:
            del _tracked_paths[self]

            if os.path.exists(self):
                os.unlink(self)
                logging.debug('TempFilePath deleted %r' % self)
            else:
                logging.warning('TempFilePath already deleted %r' % self)
        else:
            _tracked_paths[self] -= 1


def _cleanup_temp_files():
    logging.debug('_cleanup_temp_files')
    for path in list(_tracked_paths.keys()):
        try:
            os.unlink(path)
        except BaseException:
            # pylint: disable=W0702
            logging.exception('Exception occurred in _cleanup_temp_files')


atexit.register(_cleanup_temp_files)


def format_size(size):
    if not size:
        return _('Empty')
    elif size < 1024:
        return _('%d B') % size
    elif size < 1024 ** 2:
        return _('%d KB') % (size / 1024)
    elif size < 1024 ** 3:
        return _('%d MB') % (size / 1024 ** 2)
    else:
        return _('%d GB') % (size / 1024 ** 3)
