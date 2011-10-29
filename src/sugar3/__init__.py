# Copyright (C) 2006-2007, Red Hat, Inc.
# Copyright (C) 2007-2008, One Laptop Per Child
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
import gettext


if 'SUGAR_PREFIX' in os.environ:
    prefix = os.environ['SUGAR_PREFIX']
else:
    prefix = '/usr'

locale_path = os.path.join(prefix, 'share', 'locale')

gettext.bindtextdomain('sugar-base', locale_path)
