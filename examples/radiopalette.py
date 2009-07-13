import gtk

from sugar.graphics.radiopalette import RadioPalette, RadioMenuButton, \
                                        RadioToolsButton
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics import style

window = gtk.Window()

box = gtk.VBox()
window.add(box)

toolbar = gtk.Toolbar()
box.pack_start(toolbar, False)

text_view = gtk.TextView()
box.pack_start(text_view)

def echo(text):
    text_view.props.buffer.props.text += "\n" +  text

palette = RadioPalette()
palette.append(
        icon_name='document-open',
        tooltip='menu.document-open',
        toggled_cb=lambda: echo('menu.document-open'))
palette.append(
        icon_name='document-save',
        tooltip='menu.document-save',
        toggled_cb=lambda: echo('menu.document-save'))
palette.append(
        icon_name='document-send',
        tooltip='menu.document-send',
        toggled_cb=lambda: echo('menu.document-send'))

button = RadioMenuButton(palette=palette)
toolbar.insert(button, -1)

palette = RadioPalette()
palette.append(
        icon_name='document-open',
        tooltip='tools.document-open',
        toggled_cb=lambda: echo('tools.document-open'))
palette.append(
        icon_name='document-save',
        tooltip='tools.document-save',
        toggled_cb=lambda: echo('tools.document-save'))
palette.append(
        icon_name='document-send',
        tooltip='tools.document-send',
        toggled_cb=lambda: echo('tools.document-send'))

button = RadioToolsButton(palette=palette)
toolbar.insert(button, -1)

window.show_all()
gtk.main()
