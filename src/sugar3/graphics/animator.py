# Copyright (C) 2007, Red Hat, Inc.
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

import time

from gi.repository import GObject
from gi.repository import GLib

EASE_OUT_EXPO = 0
EASE_IN_EXPO = 1


class Animator(GObject.GObject):

    __gsignals__ = {
        'completed': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, duration, fps=20, easing=EASE_OUT_EXPO):
        GObject.GObject.__init__(self)
        self._animations = []
        self._duration = duration
        self._interval = 1.0 / fps
        self._easing = easing
        self._timeout_sid = 0
        self._start_time = None

    def add(self, animation):
        self._animations.append(animation)

    def remove_all(self):
        self.stop()
        self._animations = []

    def start(self):
        if self._timeout_sid:
            self.stop()

        self._start_time = time.time()
        self._timeout_sid = GLib.timeout_add(
            int(self._interval * 1000), self._next_frame_cb)

    def stop(self):
        if self._timeout_sid:
            GObject.source_remove(self._timeout_sid)
            self._timeout_sid = 0
            self.emit('completed')

    def _next_frame_cb(self):
        current_time = min(self._duration, time.time() - self._start_time)
        current_time = max(current_time, 0.0)

        for animation in self._animations:
            animation.do_frame(current_time, self._duration, self._easing)

        if current_time == self._duration:
            self.stop()
            return False
        else:
            return True


class Animation(object):

    def __init__(self, start, end):
        self.start = start
        self.end = end

    def do_frame(self, t, duration, easing):
        start = self.start
        change = self.end - self.start

        if t == duration:
            # last frame
            frame = self.end
        else:
            if easing == EASE_OUT_EXPO:
                frame = change * (-pow(2, -10 * t / duration) + 1) + start
            elif easing == EASE_IN_EXPO:
                frame = change * pow(2, 10 * (t / duration - 1)) + start

        self.next_frame(frame)

    def next_frame(self, frame):
        pass
