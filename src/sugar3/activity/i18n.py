# Copyright (C) 2010 One Laptop Per Child
#
# Author: Sayamindu Dasgupta <sayamindu@laptop.org>
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

from gettext import gettext
import struct

import dateutil.parser
import time

_MO_BIG_ENDIAN = 0xde120495
_MO_LITTLE_ENDIAN = 0x950412de


def _read_bin(handle, format_string, byte_count):
    read_bytes = handle.read(byte_count)
    return_value = struct.unpack(format_string, read_bytes)
    if len(return_value) == 1:
        return return_value[0]
    else:
        return return_value


def _extract_header(file_path):
    header = ''
    handle = open(file_path, 'rb')
    magic_number = _read_bin(handle, '<I', 4)

    if magic_number == _MO_BIG_ENDIAN:
        format_string = '>II'
    elif magic_number == _MO_LITTLE_ENDIAN:
        format_string = '<II'
    else:
        raise IOError('File does not seem to be a valid MO file')

    version_, num_of_strings = _read_bin(handle, format_string, 8)

    msgids_hash_offset, msgstrs_hash_offset = _read_bin(handle,
                                                        format_string, 8)
    handle.seek(msgids_hash_offset)

    msgids_index = []
    for i in range(num_of_strings):
        msgids_index.append(_read_bin(handle, format_string, 8))
    handle.seek(msgstrs_hash_offset)

    msgstrs_index = []
    for i in range(num_of_strings):
        msgstrs_index.append(_read_bin(handle, format_string, 8))

    for i in range(num_of_strings):
        handle.seek(msgids_index[i][1])
        msgid = handle.read(msgids_index[i][0])
        if msgid == '':
            handle.seek(msgstrs_index[i][1])
            msgstr = handle.read(msgstrs_index[i][0])
            header = msgstr
            break
        else:
            continue

    handle.close()
    return header


def _extract_modification_time(file_path):
    header = _extract_header(file_path)
    items = header.split('\n')
    for item in items:
        if item.startswith('PO-Revision-Date:'):
            time_str = item.split(': ')[1]
            parsed_time = dateutil.parser.parse(time_str)
            return time.mktime(parsed_time.timetuple())

    raise ValueError('Could not find a revision date')


# We ship our own version of pgettext() because Python 2.x will never contain
# it: http://bugs.python.org/issue2504#msg122482
def pgettext(context, message):
    """
    Return the localized translation of message, based on context and
    the current global domain, language, and locale directory.

    Similar to gettext(). Context is a string used to disambiguate
    messages that are the same in the source language (usually english),
    but might be different in one or more of the target languages.
    """
    translation = gettext('\x04'.join([context, message]))
    if '\x04' in translation:
        return message
    return translation
