# Copyright (C) 2006-2007, Red Hat, Inc.
# Copyright (C) 2007, One Laptop Per Child
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

"""MIME helpers based on freedesktop specification.

STABLE.
"""

import os
import logging
import gettext

import gi
gi.require_version('GdkPixbuf', '2.0')

from gi.repository import GLib
from gi.repository import GdkPixbuf
from gi.repository import Gio


def _(msg):
    return gettext.dgettext('sugar-toolkit-gtk3', msg)


GENERIC_TYPE_TEXT = 'Text'
GENERIC_TYPE_IMAGE = 'Image'
GENERIC_TYPE_AUDIO = 'Audio'
GENERIC_TYPE_VIDEO = 'Video'
GENERIC_TYPE_LINK = 'Link'
GENERIC_TYPE_BUNDLE = 'Bundle'


def _get_supported_image_mime_types():
    mime_types = []
    for image_format in GdkPixbuf.Pixbuf.get_formats():
        mime_types.extend(image_format.get_mime_types())
    return mime_types


_extensions = {}
_globs_timestamps = []
_subclasses = {}
_subclasses_timestamps = []

_generic_types = [{
    'id': GENERIC_TYPE_TEXT,
    'name': _('Text'),
    'icon': 'text-x-generic',
    'types': ['text/plain', 'text/rtf', 'application/pdf', 'application/x-pdf',
              'text/html', 'application/vnd.oasis.opendocument.text',
              'application/rtf', 'text/rtf', 'application/epub+zip'],
}, {
    'id': GENERIC_TYPE_IMAGE,
    'name': _('Image'),
    'icon': 'image-x-generic',
    'types': _get_supported_image_mime_types(),
}, {
    'id': GENERIC_TYPE_AUDIO,
    'name': _('Audio'),
    'icon': 'audio-x-generic',
    'types': [
        'audio/ogg', 'audio/x-wav', 'audio/wav', 'audio/x-vorbis+ogg',
        'audio/x-mpegurl', 'audio/mpegurl', 'audio/mpeg', 'audio/x-scpls'],
}, {
    'id': GENERIC_TYPE_VIDEO,
    'name': _('Video'),
    'icon': 'video-x-generic',
    'types': ['video/ogg', 'application/ogg', 'video/x-theora+ogg',
              'video/x-theora', 'video/x-mng', 'video/mpeg4',
              'video/mpeg-stream', 'video/mpeg', 'video/mpegts', 'video/mpeg2',
              'video/mpeg1', 'video/x-cdxa', 'video/x-ogm+ogg', 'video/x-flv',
              'video/mp4', 'video/x-matroska', 'video/x-msvideo',
              'application/x-ogm-video', 'video/quicktime', 'video/x-quicktime'
              'video/avi'],
}, {
    'id': GENERIC_TYPE_LINK,
    'name': _('Link'),
    'icon': 'text-uri-list',
    'types': ['text/x-moz-url', 'text/uri-list'],
}, {
    'id': GENERIC_TYPE_BUNDLE,
    'name': _('Bundle'),
    'icon': 'user-documents',
    'types': ['application/vnd.olpc-sugar'],
}]


class ObjectType(object):

    def __init__(self, type_id, name, icon, mime_types):
        self.type_id = type_id
        self.name = name
        self.icon = icon
        self.mime_types = mime_types


def get_generic_type(type_id):
    types = get_all_generic_types()
    for generic_type in types:
        if type_id == generic_type.type_id:
            return generic_type


def get_all_generic_types():
    types = []
    for generic_type in _generic_types:
        object_type = ObjectType(generic_type['id'], generic_type['name'],
                                 generic_type['icon'], generic_type['types'])
        types.append(object_type)
    return types


def get_for_file(file_name):
    if file_name.startswith('file://'):
        file_name = file_name[7:]

    file_name = os.path.realpath(file_name)

    f = Gio.File.new_for_path(file_name)
    try:
        info = f.query_info(Gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE, 0, None)
        mime_type = info.get_content_type()
    except GLib.GError:
        mime_type = Gio.content_type_guess(file_name, None)[0]

    return mime_type


def get_from_file_name(file_name):
    """
    DEPRECATED: 0.102 (removed in 4 releases)
    Use Gio.content_type_guess(file_name, None)[0] instead.
    """
    return Gio.content_type_guess(file_name, None)[0]


def get_mime_icon(mime_type):
    generic_type = _get_generic_type_for_mime(mime_type)
    if generic_type:
        return generic_type['icon']

    return mime_type.replace('/', '-')


def get_mime_description(mime_type):
    generic_type = _get_generic_type_for_mime(mime_type)
    if generic_type:
        return generic_type['name']

    return Gio.content_type_get_description(mime_type)


def get_mime_parents(mime_type):
    global _subclasses
    global _subclasses_timestamps

    dirs = _get_mime_data_directories()

    timestamps = []
    subclasses_path_list = []
    for f in dirs:
        subclasses_path = os.path.join(f, 'mime', 'subclasses')
        try:
            mtime = os.stat(subclasses_path).st_mtime
            timestamps.append([subclasses_path, mtime])
            subclasses_path_list.append(subclasses_path)
        except OSError:
            pass

    if timestamps != _subclasses_timestamps:
        _subclasses = {}
        for subclasses_path in subclasses_path_list:
            with open(subclasses_path) as parents_file:
                for line in parents_file:
                    subclass, parent = line.split()
                    if subclass not in list(_subclasses.keys()):
                        _subclasses[subclass] = [parent]
                    else:
                        _subclasses[subclass].append(parent)

        _subclasses_timestamps = timestamps

    if mime_type in list(_subclasses.keys()):
        return _subclasses[mime_type]
    else:
        return []


def _get_mime_data_directories():
    dirs = []

    if 'XDG_DATA_HOME' in os.environ:
        dirs.append(os.environ['XDG_DATA_HOME'])
    else:
        dirs.append(os.path.expanduser('~/.local/share/'))

    if 'XDG_DATA_DIRS' in os.environ:
        dirs.extend(os.environ['XDG_DATA_DIRS'].split(':'))
    else:
        dirs.extend(['/usr/local/share/', '/usr/share/'])
    return dirs


def _init_mime_information():
    global _extensions
    global _globs_timestamps

    dirs = _get_mime_data_directories()

    timestamps = []
    globs_path_list = []
    for f in dirs:
        globs_path = os.path.join(f, 'mime', 'globs')
        if os.path.exists(globs_path):
            mtime = os.stat(globs_path).st_mtime
            timestamps.append([globs_path, mtime])
            globs_path_list.append(globs_path)

    if timestamps != _globs_timestamps:
        # Clear the old extensions list
        _extensions = {}

        # FIXME Properly support these types in the system. (#4855)
        _extensions['audio/ogg'] = ['ogg']
        _extensions['video/ogg'] = ['ogg']

        for globs_path in globs_path_list:
            globs_file = open(globs_path)
            for line in globs_file.readlines():
                line = line.strip()
                if not line.startswith('#'):
                    line_type, glob = line.split(':')
                    if glob.startswith('*.'):
                        if line_type in _extensions:
                            _extensions[line_type].append(glob[2:])
                        else:
                            _extensions[line_type] = [glob[2:]]

        _globs_timestamps = timestamps


def get_primary_extension(mime_type):
    _init_mime_information()
    if mime_type in _extensions:
        return _extensions[mime_type][0]
    else:
        return None


def get_extensions_by_mimetype(mime_type):
    _init_mime_information()
    if mime_type in _extensions:
        return _extensions[mime_type]
    else:
        return []


_MIME_TYPE_BLACK_LIST = [
    # Target used only between gtk.TextBuffer instances
    'application/x-gtk-text-buffer-rich-text',
]


def choose_most_significant(mime_types):
    logging.debug('Choosing between %r.', mime_types)
    if not mime_types:
        return ''

    if 'text/uri-list' in mime_types:
        return 'text/uri-list'

    for mime_category in ['image/', 'application/']:
        for mime_type in mime_types:

            if mime_type.startswith(mime_category) and \
               mime_type not in _MIME_TYPE_BLACK_LIST:
                # skip mozilla private types (second component starts with '_'
                # or ends with '-priv')
                if mime_type.split('/')[1].startswith('_') or \
                   mime_type.split('/')[1].endswith('-priv'):
                    continue

                # take out the specifier after ';' that mozilla likes to add
                mime_type = mime_type.split(';')[0]
                logging.debug('Choosed %r!', mime_type)
                return mime_type

    if 'text/x-moz-url' in mime_types:
        logging.debug('Choosed text/x-moz-url!')
        return 'text/x-moz-url'

    if 'text/html' in mime_types:
        logging.debug('Choosed text/html!')
        return 'text/html'

    if 'text/plain' in mime_types:
        logging.debug('Choosed text/plain!')
        return 'text/plain'

    logging.debug('Returning first: %r.', mime_types[0])
    return mime_types[0]


def split_uri_list(uri_list):
    return GLib.uri_list_extract_uris(uri_list)


def _get_generic_type_for_mime(mime_type):
    for generic_type in _generic_types:
        if mime_type in generic_type['types']:
            return generic_type
    return None
