# Copyright (C) 2008 One Laptop Per Child
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation; either version 2.1 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""Subclass of TubeConnection that converts handles to Sugar Buddies

STABLE.
"""

from sugar3.presence.tubeconn import TubeConnection
from sugar3.presence import presenceservice
from gi.repository import TelepathyGLib

CHANNEL_GROUP_FLAG_CHANNEL_SPECIFIC_HANDLES = \
    TelepathyGLib.ChannelGroupFlags.CHANNEL_SPECIFIC_HANDLES


class SugarTubeConnection(TubeConnection):
    """Subclass of TubeConnection that converts handles to Sugar Buddies"""

    def __new__(cls, conn, tubes_iface, tube_id, address=None,
                group_iface=None, mainloop=None):
        self = super(SugarTubeConnection, cls).__new__(
            cls, conn, tubes_iface, tube_id, address=address,
            group_iface=group_iface, mainloop=mainloop)
        self._conn = conn
        self._group_iface = group_iface
        return self

    def get_buddy(self, cs_handle):
        """Retrieve a Buddy object given a telepathy handle.

        cs_handle: A channel-specific CONTACT type handle.
        returns: sugar3.presence Buddy object or None
        """
        pservice = presenceservice.get_instance()
        if self.self_handle == cs_handle:
            # It's me, just get my global handle
            handle = self._conn.GetSelfHandle()
        elif self._group_iface.GetGroupFlags() & \
                CHANNEL_GROUP_FLAG_CHANNEL_SPECIFIC_HANDLES:
            # The group (channel) has channel specific handles
            handle = self._group_iface.GetHandleOwners([cs_handle])[0]
        else:
            # The group does not have channel specific handles
            handle = cs_handle

        # deal with failure to get the handle owner
        if handle == 0:
            return None
        return pservice.get_buddy_by_telepathy_handle(
            self._conn.service_name, self._conn.object_path, handle)
