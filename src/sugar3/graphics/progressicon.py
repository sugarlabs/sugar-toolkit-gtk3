# Copyright (C) 2013, One Laptop Per Child
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
'''
The progressicon module provides a progress icon; a widget like progress
bar which shows progress of a task 
'''

from gi.repository import Gtk
from sugar3.graphics.icon import get_surface
from sugar3.graphics import style
 
class ProgressIcon(Gtk.DrawingArea): '''UI interface for Progress Icon.'''
 '''This class is compatible with the sugar3.graphics.icon.Icon class.
    Sets stroke color (border color of progressicon) to transparent.
    Sets fill color to transparent. 
 '''
    def __init__(self, icon_name, pixel_size, stroke_color, fill_color, 
                 direction='vertical'):
        ''' 
        
        Initializes the ProgressIcon class
        
        Parameters:
           icon_name - The name of icon progressicon uses.
           pixel_size - It explains basic geometry of an image. 
           stroke_color - Stroke color means border color. Here, it is for progressicon.
           fill_color - The inside color of progressicon.
        
        '''
        
        Gtk.DrawingArea.__init__(self) '''here, init stands for initializer, self represents instance of __init__'''

        self._icon_name = icon_name 
        self._direction = direction 
        self._progress = 0

        self._stroke = get_surface(
            icon_name=icon_name, width=pixel_size, height=pixel_size,
            stroke_color=stroke_color,
            fill_color=style.COLOR_TRANSPARENT.get_svg())
           
        self._fill = get_surface(
            icon_name=icon_name, width=pixel_size, height=pixel_size,
            stroke_color=style.COLOR_TRANSPARENT.get_svg(),
            fill_color=fill_color)
            
        self.connect("draw", self.__draw_cb)

    def __draw_cb(self, widget, cr):
     
        allocation = widget.get_allocation() 
        
        '''
        Retruns:
           A gtk.gdk.Rectangle
           The get_allocation() method returns a rectangle containing the bounds of the widget's allocation.
        '''
        
        # Center the graphic in the allocated space.
        margin_x = (allocation.width - self._stroke.get_width()) / 2 
        margin_y = (allocation.height - self._stroke.get_height()) / 2 
        cr.translate(margin_x, margin_y)

        # Paint the fill, clipping it by the progress.
        x_, y_ = 0, 0 '''The value of margin x_ and y_ is 0,0 (0i,0j) '''
        width, height = self._stroke.get_width(), self._stroke.get_height() '''Width = self._stroke.get_width() & height = self._stroke.get_height()'''
        if self._direction == 'vertical':  #vertical direction, bottom to top 
            y_ = self._stroke.get_height()
            height *= self._progress * -1
        else: 
            rtl_direction = \
                Gtk.Widget.get_default_direction() == Gtk.TextDirection.RTL '''Sets text direction from right to left'''
            if rtl_direction: # horizontal direction, right to left
                x_ = self._stroke.get_width() 
                width *= self._progress * -1
            else: # horizontal direction, left to right
                width *= self._progress
         '''
          The direction defaults to 'vertical', in which case the icon is
          filled from bottom to top.  If direction is set to 'horizontal',
          it will be filled from right to left or from left to right,
          depending on the system's language RTL setting.
          '''
        cr.rectangle(x_, y_, width, height)
        cr.clip() 
        cr.set_source_surface(self._fill, 0, 0)
        cr.paint() 

        # Paint the stroke over the fill.
        cr.reset_clip() 
        cr.set_source_surface(self._stroke, 0, 0)
        cr.paint()

    def do_get_preferred_width(self):
        width = self._stroke.get_width() 
        return (width, width) 
        '''
        Returns:
        
            Width for progressicon. Width will be set to _stroke.get_width()
       
        Example:
            from gi.repository import Gtk
            class Patch(Gtk.DrawingArea):
            def __init__(self):
            super(Patch,self).__init__()

            def do_get_preferred_width(self):
            print("example")
            return 100, 100
        '''

    def do_get_preferred_height(self):
        height = self._stroke.get_height()
        return (height, height) '''Returns tuple'''
        '''
        Returns:
        
            Width for progressicon. Height will be set to _stroke.get_height()
        
        Example:
            from gi.repository import Gtk
            class Patch(Gtk.DrawingArea):
            def __init__(self):
            super(Patch,self).__init__()

            def do_get_preferred_height(self):
            print("example")
            return (100, 100)
        '''

    def update(self, progress): '''updates progressicon with progress value '''
        self._progress = progress '''Set progressbar value'''
        self.queue_draw() 
        '''
         Call update(progress) with the new progress to update the icon.
         Updates progressicon with progress value 
        
        Example:
            update(0.9)
            
         '''
