from gi.repository import Gtk

from sugar3.graphics import animator
from sugar3.graphics.icon import Icon
from sugar3.graphics import style

from common import set_theme
set_theme()


class _Animation(animator.Animation):

    def __init__(self, icon, start_size, end_size):
        animator.Animation.__init__(self, 0.0, 1.0)

        self._icon = icon
        self.start_size = start_size
        self.end_size = end_size

    def next_frame(self, current):
        d = (self.end_size - self.start_size) * current
        self._icon.props.pixel_size = int(self.start_size + d)


def __animation_completed_cb(anim):
    print 'Animation completed'


w = Gtk.Window()
w.connect('delete-event', Gtk.main_quit)

box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
w.add(box)

anim = animator.Animator(5)
anim.connect('completed', __animation_completed_cb)

my_icon = Icon(icon_name='go-next')
box.pack_start(my_icon, False, False, 0)

anim.add(_Animation(my_icon, style.STANDARD_ICON_SIZE, style.XLARGE_ICON_SIZE))
anim.start()

w.show_all()

Gtk.main()
