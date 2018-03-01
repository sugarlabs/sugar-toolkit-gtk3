# Copyright (C) 2007 Red Hat, Inc.
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
STABLE.
"""

from gi.repository import GObject


_groups = {}


def get_group(group_id):
    if group_id in _groups:
        group = _groups[group_id]
    else:
        group = Group()
        _groups[group_id] = group

    return group


def popdown_all():
    for group in list(_groups.values()):
        group.popdown()


class Group(GObject.GObject):

    __gsignals__ = {
        'popup': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'popdown': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self._up = False
        self._palettes = []
        self._sig_ids = {}

    def is_up(self):
        return self._up

    def get_state(self):
        for palette in self._palettes:
            if palette.is_up():
                return palette.palette_state

        return None

    def add(self, palette):
        self._palettes.append(palette)

        self._sig_ids[palette] = []

        sid = palette.connect('popup', self._palette_popup_cb)
        self._sig_ids[palette].append(sid)

        sid = palette.connect('popdown', self._palette_popdown_cb)
        self._sig_ids[palette].append(sid)

    def remove(self, palette):
        if palette not in self._palettes:
            # This happens when converting a window based palette to a menu
            # based one.
            return

        sig_ids = self._sig_ids[palette]
        for sid in sig_ids:
            palette.disconnect(sid)

        self._palettes.remove(palette)
        del self._sig_ids[palette]

    def popdown(self):
        for palette in self._palettes:
            if palette.is_up():
                palette.popdown(immediate=True)

    def _palette_popup_cb(self, palette):
        for i in self._palettes:
            if i != palette:
                i.popdown(immediate=True)
        if not self._up:
            self.emit('popup')
            self._up = True

    def _palette_popdown_cb(self, palette):
        down = True
        for palette in self._palettes:
            if palette.is_up():
                down = False

        if down:
            self._up = False
            self.emit('popdown')
