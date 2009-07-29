import gtk

from sugar.graphics.radiopalette import RadioPalette, RadioMenuButton, \
                                        RadioToolsButton
from sugar.graphics.radiotoolbutton import RadioToolButton
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics import style

window = gtk.Window()

box = gtk.VBox()
window.add(box)

toolbar = gtk.Toolbar()
box.pack_start(toolbar, False)

text_view = gtk.TextView()
box.pack_start(text_view)

def echo(button):
    if not button.props.active:
        return
    text_view.props.buffer.props.text += "\n" + button.props.tooltip

# RadioMenuButton

palette = RadioPalette()

group = RadioToolButton(
        icon_name='document-open',
        tooltip='menu.document-open')
group.connect('clicked', lambda button: echo(button))
palette.append(group)

button = RadioToolButton(
        icon_name='document-save',
        group=group,
        tooltip='menu.document-save')
button.connect('clicked', lambda button: echo(button))
palette.append(button)

button = RadioToolButton(
        icon_name='document-send',
        group=group,
        tooltip='menu.document-send')
button.connect('clicked', lambda button: echo(button))
palette.append(button)

button = RadioMenuButton(palette=palette)
toolbar.insert(button, -1)

# RadioToolsButton

palette = RadioPalette()

group = RadioToolButton(
        icon_name='document-open',
        tooltip='menu.document-open')
group.connect('clicked', lambda button: echo(button))
palette.append(group)

button = RadioToolButton(
        icon_name='document-save',
        group=group,
        tooltip='menu.document-save')
button.connect('clicked', lambda button: echo(button))
palette.append(button)

button = RadioToolButton(
        icon_name='document-send',
        group=group,
        tooltip='menu.document-send')
button.connect('clicked', lambda button: echo(button))
palette.append(button)

button = RadioToolsButton(palette=palette)
toolbar.insert(button, -1)

window.show_all()
gtk.main()
