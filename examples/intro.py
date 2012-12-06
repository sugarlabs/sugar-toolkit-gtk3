from gi.repository import Gtk
from common import set_theme
from jarabe.intro.window import IntroWindow

set_theme()
win = IntroWindow()
win.show_all()
Gtk.main()
