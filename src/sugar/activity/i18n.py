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

import gconf

import locale
import os
import struct
import sys

import dateutil.parser
import time

_MO_BIG_ENDIAN    = 0xde120495
_MO_LITTLE_ENDIAN = 0x950412de

def _readbin(handle, fmt, bytecount):
    read_bytes = handle.read(bytecount)
    retvalue = struct.unpack(fmt, read_bytes)
    if len(retvalue) == 1:
        return retvalue[0]
    else:
        return retvalue

def _extract_header(filepath):
    header = ''
    handle = open(filepath, 'rb')
    magic_number = _readbin(handle, '<I', 4)

    if magic_number == _MO_BIG_ENDIAN:
        fmt = '>II'
    elif magic_number == _MO_LITTLE_ENDIAN:
        fmt = '<II'
    else:
        raise IOError ('File does not seem to be valid MO file')

    version, numofstrings = _readbin(handle, fmt, 8)

    msgids_hash_offset, msgstrs_hash_offset = _readbin(handle, fmt, 8)
    handle.seek(msgids_hash_offset)

    msgids_index = []
    for i in range(numofstrings):
        msgids_index.append(_readbin(handle, fmt, 8))
    handle.seek(msgstrs_hash_offset)

    msgstrs_index = []
    for i in range(numofstrings):
        msgstrs_index.append(_readbin(handle, fmt, 8))

    for i in range(numofstrings):
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

def _extract_modification_time(filepath):
    header = _extract_header(filepath)
    items = header.split('\n')
    for item in items:
        if item.startswith('PO-Revision-Date:'):
            timestr = item.split(': ')[1]
            parsedtime = dateutil.parser.parse(timestr)
            return time.mktime(parsedtime.timetuple())

    raise ValueError ('Could not find revision date')
    return -1


def get_locale_path(bundle_id):
    """ Gets the locale path, the directory where the preferred 
        MO file is located.
        The preferred MO file is the one with the latest 
        translation.
    """
    
    # Note: We pre-assign weights to the directories so that if no translations
    # exist, the appropriate fallbacks (eg: bn for bn_BD) can be loaded
    # The directory with the highest weight is returned, and if a MO file is
    # found, the weight of the directory is set to the MO's modification time
    # (as described in the MO header, and _not_ the filesystem mtime)
    
    candidate_dirs = {}

    if 'SUGAR_LOCALEDIR' in os.environ:
        candidate_dirs[os.environ['SUGAR_LOCALEDIR']] = 2
    
    gconf_client = gconf.client_get_default()
    packdir = gconf_client.get_string("/desktop/sugar/i18n/langpackdir")
    if packdir is not None or packdir is not '':
        candidate_dirs[packdir] = 1
    
    candidate_dirs[os.path.join(sys.prefix, 'share', 'locale')] = 0

    for candidate_dir in candidate_dirs.keys():
        if os.path.exists(candidate_dir):
            fullpath = os.path.join(candidate_dir, \
                locale.getdefaultlocale()[0], 'LC_MESSAGES', \
                bundle_id + '.mo')
            if os.path.exists(fullpath):
                try:
                    candidate_dirs[candidate_dir] = \
                        _extract_modification_time(fullpath)
                except (IOError, ValueError):
                    # The mo file is damaged or has not been initialized
                    # Set lowest priority
                    candidate_dirs[candidate_dir] = -1

    return sorted(candidate_dirs.iteritems(), key=lambda (k, v): (v, k), \
        reverse = True)[0][0]
