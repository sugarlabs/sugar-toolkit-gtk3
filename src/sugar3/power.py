# Copyright (C) 2014, Sugarlabs
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
import logging

_POWERD_INHIBIT_DIR = '/var/run/powerd-inhibit-suspend'


class PowerManager():
    """ control of powerd idle suspend,
        reference counted,
        does nothing if powerd is not present
    """

    def __init__(self):
        self._references = 0

    def __del__(self):
        self._remove_flag_file()

    def inhibit_suspend(self):
        if not os.path.exists(_POWERD_INHIBIT_DIR):
            return

        if self._references == 0:
            path = os.path.join(_POWERD_INHIBIT_DIR, str(os.getpid()))
            try:
                with open(path, 'w') as flag_file:
                    flag_file.write('')
            except IOError:
                logging.error("Inhibit Suspend: Could not create file %s",
                              path)

        self._references += 1

    def restore_suspend(self):
        self._references -= 1
        if self._references > 0:
            return
        # if == 0
        self._remove_flag_file()

    def _remove_flag_file(self):
        path = os.path.join(_POWERD_INHIBIT_DIR, str(os.getpid()))
        try:
            os.unlink(path)
        except IOError:
            logging.error("Inhibit Suspend: Could not delete file %s", path)
        self._references = 0
