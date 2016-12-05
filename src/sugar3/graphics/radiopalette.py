# Copyright (C) 2009, Aleksey Lim
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

from gi.repository import Gtk

from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.palette import Palette

'''
This file is used to open a palette with a bunch 
of widgets, some of whom are clickable while the others
are not. Also, the buttons can have sub-palettes or menus.

RadioPalette is different from a normal palette, as: in a 
normal palette you can add only one widget but in this you 
can add multiple of them (because internally they are HBox'es)

This class dynamically switches between the window widget and the 
menu widget.
The window widget, created by default, acts as the container for any
type of widget the user may wish to add. It is made to display 
an icon at the top of the palette, but it can be used to display 
anything with the "clicked" event

Example: radiopalette.py

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
'''

class RadioMenuButton(ToolButton):
    '''
    This is a button used to open a group of widgets in a RadioPalette(menu)
    It does not react if one clicks on it, as you can see this class does not
    have a funnction which reacts to a click.
    Example usage: button = "RadioMenuButton(palette=palette)"
    '''

    def __init__(self, **kwargs):
        ToolButton.__init__(self, **kwargs)
        self.selected_button = None

        self.palette_invoker.props.toggle_palette = True
        self.props.hide_tooltip_on_click = False

        if self.props.palette:
            self.__palette_cb(None, None)

        self.connect('notify::palette', self.__palette_cb)

    def __palette_cb(self, widget, pspec):
        '''
        A callback function
        it returns if the "self.props.palette" is an instance of "RadioPalette",
        if it is not, then it updates the button with the function "update_button()"
        '''
        if not isinstance(self.props.palette, RadioPalette):
            return
        self.props.palette.update_button()


class RadioToolsButton(RadioMenuButton):
    '''
    This is a button used to open a group of widgets in a RadioPalette(menu)
    It is essentially just a RadioMenuButton but with the added function
    do_clicked(self), which performs the given lines of code.    
    Example Usage: button = RadioToolButton(icon_name='document-save',
                                            group=group)
    where icon_name and group are Kwargs parameters
    '''

    def __init__(self, **kwargs):
        RadioMenuButton.__init__(self, **kwargs)

    def do_clicked(self):
        '''
        This function is called when RadioToolsButton is clicked,
        it checks if the button is selected or not, in case that it is 
        not, it returns without doing anything, but if it is, it emits
        the signal 'clicked'
        '''
        if not self.selected_button:
            return
        self.selected_button.emit('clicked')


class RadioPalette(Palette):
    '''
    This contains the widgets to be displayed in the RadioMenuButton
    and RadioToolsButton. This is the Palette (menu) that shows up when
    those buttons are clicked. It is used to display the widgets.
    It is a Gtk HBox, with the functions append(),update_button() and
    __clicked_cb() as defined below.
    Example Usage: palette = RadioPalette()
    '''
    def __init__(self, **kwargs):
        Palette.__init__(self, **kwargs)

        self.button_box = Gtk.HBox()
        self.button_box.show()
        self.set_content(self.button_box)

    def append(self, button, label):
        '''
        Adds a widget to the RadioPalette
        "button": the button to be added to the Palette is being passed
        "label": is the what wants to be set to "button.palette_label"
        This function, adds the Button if it does not have sub-palettes.
        displays it on the screen (.show()), connects it with the listener
        function which checks when the button gets clicked and lastly it 
        pushes the given label as the button's palette label.
        It also clicks the button if it does not have children.
        '''
        children = self.button_box.get_children()

        if button.palette is not None:
            raise RuntimeError("Palette's button should not have sub-palettes")

        button.show()
        button.connect('clicked', self.__clicked_cb)
        self.button_box.pack_start(button, True, False, 0)
        button.palette_label = label

        if not children:
            self.__clicked_cb(button)

    def update_button(self):
        '''
        Updates the button, as what would happen if someone
        clicked all the elements of the button_box.
        '''
        for i in self.button_box.get_children():
            self.__clicked_cb(i)

    def __clicked_cb(self, button):
        '''
        Called when an element in RadioPalette is clicked 
        Changes the label text to reflect the change in the selection
        with the help of the function "set_primary_text(button.palette_label)"
        which passes the label as the parameter
        Creates the pop down for the selected widget with the function
        popdown(immediate=True)
        and also changes the parent's label icon and selected button in 
        the last three lines of the code
        '''
        if not button.get_active():
            return

        self.set_primary_text(button.palette_label)
        self.popdown(immediate=True)

        if self.invoker is not None:
            parent = self.invoker.parent
        else:
            parent = None
        if not isinstance(parent, RadioMenuButton):
            return

        parent.props.label = button.palette_label
        parent.set_icon_name(button.props.icon_name)
        parent.selected_button = button
