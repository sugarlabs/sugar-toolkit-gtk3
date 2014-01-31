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

_power_manager = None


def get_power_manager():
    global _power_manager
    if _power_manager is None:
        _power_manager = PowerManager()
    return _power_manager


class PowerManager():
    """ control of powerd idle suspend,
        reference counted,
        does nothing if powerd is not present
    """

    def __init__(self):
        self._suspend_inhibit_counter = 0

    def __del__(self):
        self._remove_flag_file()

    def suspend_breaks_collaboration(self):
        return True

    def inhibit_suspend(self):
        if not os.path.exists(_POWERD_INHIBIT_DIR):
            return

        if self._suspend_inhibit_counter == 0:
            path = os.path.join(_POWERD_INHIBIT_DIR, str(os.getpid()))
            try:
                with open(path, 'w') as flag_file:
                    flag_file.write('')
            except IOError:
                logging.error("Inhibit Suspend: Could not create file %s",
                              path)

        self._suspend_inhibit_counter += 1

    def restore_suspend(self):
        self._suspend_inhibit_counter -= 1
        if self._suspend_inhibit_counter > 0:
            return
        self._remove_flag_file()

    def is_suspend_inhibited(self):
        return self._suspend_inhibit_counter > 0

    def shutdown(self):
        """
        This method clean the flag file if exists,
        is already called when the activity is closed.
        """
        self._remove_flag_file()

    def _remove_flag_file(self):
        path = os.path.join(_POWERD_INHIBIT_DIR, str(os.getpid()))
        try:
            os.unlink(path)
        except OSError:
            logging.error("Inhibit Suspend: Could not delete file %s", path)
        self._suspend_inhibit_counter = 0
