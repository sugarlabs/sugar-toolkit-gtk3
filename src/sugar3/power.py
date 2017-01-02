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

"""
The power module provides an interface to *powerd*, a daemon that
manages the aggressive suspend and wakeup policies for early OLPC
laptops.

The module does nothing if *powerd* is not present.  *powerd* is not
required on laptops other than OLPC XO-1, XO-1.5, XO-1.75 and XO-4.
Distributions of Sugar on other hardware need not include the *powerd*
package.
"""

import os
import logging

_POWERD_INHIBIT_DIR = '/var/run/powerd-inhibit-suspend'

_power_manager = None


def get_power_manager():
    """
    Get the power manager instance.  Only one instance exists, and
    will always be returned.

    Returns:
        an instance of :class:`sugar3.power.PowerManager`.
    """
    global _power_manager
    if _power_manager is None:
        _power_manager = PowerManager()
    return _power_manager


class PowerManager():
    """
    Control of automatic idle suspend, with reference counting.

    :class:`sugar3.activity.activity.Activity` calls
    :py:meth:`inhibit_suspend` before speaking text, or when an
    activity collaboration begins.

    Activities may call :py:meth:`inhibit_suspend` before playing
    music, video, speaking large amounts of text, collaborating, or
    waiting for response to network operations.

    As an example, the Clock activity inhibits automatic idle suspend
    while it is active, so that the displayed clock-face continues to
    change.  Otherwise it would freeze.

    :class:`sugar3.activity.activity.Activity` calls
    :py:meth:`shutdown` as an activity terminates, in case the
    activity has failed to call :py:meth:`restore_suspend`.

    While automatic idle suspend is inhibited, *powerd* will
    continue to dim and blank the display.

    Both the :py:meth:`inhibit_suspend` and :py:meth:`restore_suspend`
    methods are reference counted; automatic idle suspend is not
    restored until the same number of calls to restore are made.

    *powerd* is resilient against failure to restore automatic idle
    suspend; it verifies an inhibit request and deletes it if the
    requesting process has terminated.
    """

    def __init__(self):
        self._suspend_inhibit_counter = 0
        if os.path.exists(_POWERD_INHIBIT_DIR):
            self._path = os.path.join(_POWERD_INHIBIT_DIR, str(os.getpid()))
        else:
            self._path = None

    def __del__(self):
        self._remove_flag_file()

    def suspend_breaks_collaboration(self):
        """
        Does automatic idle suspend break collaboration with this
        toolkit?  Yes.  For future use by a toolkit with more
        resilient collaboration.

        Returns:
            True
        """
        return True

    def inhibit_suspend(self):
        """
        Inhibit automatic idle suspend until restored.
        """
        if self._path and self._suspend_inhibit_counter == 0:
            try:
                with open(self._path, 'w') as flag_file:
                    flag_file.write('')
            except IOError:
                logging.error("Inhibit Suspend: Could not create file %s",
                              self._path)

        self._suspend_inhibit_counter += 1

    def restore_suspend(self):
        """
        Possibly restore automatic idle suspend.
        """
        self._suspend_inhibit_counter -= 1
        if self._suspend_inhibit_counter > 0:
            return
        self._remove_flag_file()

    def is_suspend_inhibited(self):
        """
        Check if automatic idle suspend is inhibited.

        Returns:
            inhibited (bool): whether automatic idle suspend is inhibited.
        """
        return self._suspend_inhibit_counter > 0

    def shutdown(self):
        """
        Shutdown the power manager.

        Restores automatic idle suspend regardless of reference counting.
        """
        self._remove_flag_file()

    def _remove_flag_file(self):
        if self._path:
            try:
                os.unlink(self._path)
            except OSError:
                pass
        self._suspend_inhibit_counter = 0
