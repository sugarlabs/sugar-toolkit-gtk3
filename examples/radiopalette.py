from gi.repository import Gtk

from sugar3.graphics.radiopalette import RadioPalette, RadioMenuButton, \
    RadioToolsButton
from sugar3.graphics.radiotoolbutton import RadioToolButton

window = Gtk.Window()

box = Gtk.VBox()
window.add(box)

toolbar = Gtk.Toolbar()
box.pack_start(toolbar, False, True, 0)

text_view = Gtk.TextView()
box.pack_start(text_view, True, True, 0)


def echo(button, label):
    if not button.props.active:
        return
    text_view.props.buffer.props.text += '\n' + label

# RadioMenuButton

palette = RadioPalette()

group = RadioToolButton(
    icon_name='document-open')
group.connect('clicked', lambda button: echo(button, 'document-open'))
palette.append(group, 'menu.document-open')

button = RadioToolButton(
    icon_name='document-save',
    group=group)
button.connect('clicked', lambda button: echo(button, 'document-save'))
palette.append(button, 'menu.document-save')

button = RadioToolButton(
    icon_name='document-send',
    group=group)
button.connect('clicked', lambda button: echo(button, 'document-send'))
palette.append(button, 'menu.document-send')

button = RadioMenuButton(palette=palette)
toolbar.insert(button, -1)

# RadioToolsButton

palette = RadioPalette()

group = RadioToolButton(
    icon_name='document-open')
group.connect('clicked', lambda button: echo(button, 'document-open'))
palette.append(group, 'menu.document-open')

button = RadioToolButton(
    icon_name='document-save',
    group=group)
button.connect('clicked', lambda button: echo(button, 'document-save'))
palette.append(button, 'menu.document-save')

button = RadioToolButton(
    icon_name='document-send',
    group=group)
button.connect('clicked', lambda button: echo(button, 'document-send'))
palette.append(button, 'menu.document-send')

button = RadioToolsButton(palette=palette)
toolbar.insert(button, -1)

window.show_all()
Gtk.main()
