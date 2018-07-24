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
The animator module provides a simple framework to create animations.

Example:
    Animate the size of a window::

        from gi.repository import Gtk
        from sugar3.graphics.animator import Animator, Animation

        # Construct a window to animate
        w = Gtk.Window()
        w.connect('destroy', Gtk.main_quit)
        # Start the animation when the window is shown
        w.connect('realize', lambda self: animator.start())
        w.show()

        # Construct a 5 second animator
        animator = Animator(5, widget=w)

        # Create an animation subclass to animate the widget
        class SizeAnimation(Animation):
            def __init__(self):
                # Tell the animation to give us values between 20 and
                # 420 during the animation
                Animation.__init__(self, 20, 420)

            def next_frame(self, frame):
                size = int(frame)
                w.resize(size, size)
        # Add the animation the the animator
        animation = SizeAnimation()
        animator.add(animation)

        # The animation needs to run inside a GObject main loop
        Gtk.main()

STABLE.
"""

import time

from gi.repository import GObject
from gi.repository import GLib

EASE_OUT_EXPO = 0
EASE_IN_EXPO = 1


class Animator(GObject.GObject):
    '''
    The animator class manages the timing for calling the
    animations.  The animations can be added using the `add` function
    and then started with the `start` function.  If multiple animations
    are added, then they will be played back at the same time and rate
    as each other.

    The `completed` signal is emitted upon the completion of the
    animation and also when the `stop` function is called.

    Args:
        duration (float): the duration of the animation in seconds
        fps (int, optional): the number of animation callbacks to make
            per second (frames per second)
        easing (int): the desired easing mode, either `EASE_OUT_EXPO`
            or `EASE_IN_EXPO`
        widget (:class:`Gtk.Widget`): one of the widgets that the animation
            is acting on.  If supplied and if the user's Gtk+ version
            supports it, the animation will run on the frame clock of the
            widget, resulting in a smoother animation and the fps value
            will be disregarded.

    .. note::

        When creating an animation, take into account the limited cpu power
        on some devices, such as the XO.  Setting the fps too high on can
        use significant cpu usage on the XO.
    '''

    __gsignals__ = {
        'completed': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, duration, fps=20, easing=EASE_OUT_EXPO, widget=None):
        GObject.GObject.__init__(self)
        self._animations = []
        self._duration = duration
        self._interval = 1.0 / fps
        self._easing = easing
        self._widget = widget
        self._timeout_sid = 0
        self._start_time = None

    def add(self, animation):
        '''
        Add an animation to this animator

        Args:
            animation (:class:`sugar3.graphics.animator.Animation`):
                the animation instance to add
        '''
        self._animations.append(animation)

    def remove_all(self):
        '''
        Remove all animations and stop this animator
        '''
        self.stop()
        self._animations = []

    def start(self):
        '''
        Start the animation running.  This will stop and restart the
        animation if the animation is currently running
        '''
        if self._timeout_sid:
            self.stop()

        self._start_time = time.time()
        if hasattr(self._widget, 'add_tick_callback'):
            self._timeout_sid = self._widget.add_tick_callback(
                self._next_frame_cb, None)
            # Make sure the 1st frame is animated so we get ticks
            self._next_frame_cb()
        else:
            self._timeout_sid = GLib.timeout_add(
                int(self._interval * 1000), self._next_frame_cb)

    def stop(self):
        '''
        Stop the animation and emit the `completed` signal
        '''
        for animation in self._animations:
            animation.do_stop()

        if self._timeout_sid and \
           not hasattr(self._widget, 'add_tick_callback'):
            GLib.source_remove(self._timeout_sid)
            self._timeout_sid = 0
            self.emit('completed')
        if self._timeout_sid and hasattr(self._widget, 'add_tick_callback'):
            self._widget.remove_tick_callback(self._timeout_sid)
            self._timeout_sid = 0
            self.emit('completed')

    def _next_frame_cb(self, *args):
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
    '''
    The animation class is a base class for creating an animation.
    It should be subclassed.  Subclasses should specify a `next_frame`
    function to set the required properties based on the animation
    progress.  The range of the `frame` value passed to the `next_frame`
    function is defined by the `start` and `end` values.

    Args:
        start (float): the first `frame` value for the `next_frame` method
        end (float): the last `frame` value for the `next_frame` method

    .. code-block:: python

        # Create an animation subclass
        class MyAnimation(Animation):
            def __init__(self, thing):
                # Tell the animation to give us values between 0.0 and
                # 1.0 during the animation
                Animation.__init__(self, 0.0, 1.0)
                self._thing = thing

            def next_frame(self, frame):
                # Use the `frame` value to set properties
                self._thing.set_green_value(frame)
    '''

    def __init__(self, start, end):
        self.start = start
        self.end = end

    def do_frame(self, t, duration, easing):
        '''
        This method is called by the animator class every frame.  This
        method calculated the `frame` value to then call `next_frame`.

        Args:
            t (float): the current time elapsed of the animation in seconds
            duration (float): the length of the animation in seconds
            easing (int): the easing mode passed to the animator
        '''
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
        '''
        This method is called every frame and should be overridden by
        subclasses.

        Args:
            frame (float): a value between `start` and `end` representing
                the current progress in the animation
        '''
        pass

    def do_stop(self):
        '''
        This method is called whenever the animation is stopped, either
        due to the animation ending or being stopped by the animation.
        `next_frame` will not be called after do_stop, unless the animation
        is restarted.

        .. versionadded:: 0.109.0.3

        This should be used in subclasses if they bind any signals.  Eg.
        if they bind the draw signal for a widget:

        .. code-block:: python

            class SignalAnimation(Animation):

                def __init__(self, widget):
                    Animation.__init__(self, 0, 1)
                    self._draw_hid = None
                    self._widget = widget

                def next_frame(self, frame):
                    self._frame = frame
                    if self._draw_hid is None:
                        self._draw_hid = self._widget.connect_after(
                            'draw', self.__draw_cb)
                    self._widget.queue_draw()

                def __draw_cb(self, widget, cr):
                    cr.save()
                    # Do the draw
                    cr.restore()

                def do_stop(self):
                    self._widget.disconnect(self._draw_hid)
                    self._widget.queue_draw()

        '''
        pass
