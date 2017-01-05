from gi.repository import Gtk

from sugar3.graphics.radiotoolbutton import RadioToolButton
from sugar3.graphics.radiopalette import RadioPalette, RadioMenuButton
from sugar3.graphics.xocolor import XoColor


window = Gtk.Window()
window.show()
window.connect("destroy", Gtk.main_quit)

box = Gtk.HBox()
window.add(box)
box.show()


def echo(button, label):
    if not button.props.active:
        return
    print label


palette = RadioPalette()
# Adding 3 RadioToolButtons to a palette

button1 = RadioToolButton(icon_name='document-save', accelerator="<ctrl>S",
                          xo_color=XoColor("white"))
button1.connect('toggled', lambda button: echo(button, 'document-save'))
palette.append(button1, 'menu.document-save')

button2 = RadioToolButton(icon_name='document-open', accelerator="<ctrl>O",
                          xo_color=XoColor("white"), group=button1)
button2.connect('toggled', lambda button: echo(button, 'document-open'))
palette.append(button2, 'menu.document-open')

button3 = RadioToolButton(icon_name='document-send', accelerator="<ctrl>F",
                          xo_color=XoColor("white"), group=button1)
button3.connect('toggled', lambda button: echo(button, 'document-send'))
palette.append(button3, 'menu.document-send')

button = RadioMenuButton(palette=palette)
box.pack_start(button, False, False, 1)
button.show()

if __name__ == '__main__':
    Gtk.main()
