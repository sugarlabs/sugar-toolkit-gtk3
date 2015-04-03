# Copyright (C) 2013 One Laptop per Child
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

import os

from gi.repository import Gio

from sugar3.bundle.activitybundle import ActivityBundle
from sugar3.bundle.contentbundle import ContentBundle


def bundle_from_archive(path, mime_type=None):
    """
    Return an appropriate Bundle object for a given file path.
    The bundle type is identified by mime_type, which is guessed if not
    provided.
    """
    if mime_type is None:
        mime_type, certainty = Gio.content_type_guess(path, data=None)
    if mime_type == ActivityBundle.MIME_TYPE:
        return ActivityBundle(path)
    elif mime_type == ContentBundle.MIME_TYPE:
        return ContentBundle(path)
    return None


def bundle_from_dir(path):
    """
    Return an appropriate Bundle object for a given directory containing
    an unzipped bundle.
    """
    if os.path.exists(os.path.join(path, 'activity', 'activity.info')):
        return ActivityBundle(path)
    elif os.path.exists(os.path.join(path, 'library', 'library.info')):
        return ContentBundle(path)
    return None
