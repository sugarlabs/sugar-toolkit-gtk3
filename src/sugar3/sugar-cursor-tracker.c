/*
 * Copyright (C) 2012 One laptop per child
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 *
 * Author: Simon Schampijer  <simon@laptop.org>
 */

#include <gtk/gtk.h>
#include <gio/gio.h> 
#ifdef GDK_WINDOWING_X11
#include <gdk/x11/gdkx.h>
#endif
#include <X11/extensions/XInput2.h>
#include <X11/extensions/Xfixes.h>
#include "sugar-cursor-tracker.h"

G_DEFINE_TYPE_WITH_PRIVATE (SugarCursorTracker, sugar_cursor_tracker, G_TYPE_OBJECT)

static void
sugar_cursor_tracker_finalize (GObject *object)
{
    G_OBJECT_CLASS (sugar_cursor_tracker_parent_class)->finalize (object);
}

static void
sugar_cursor_tracker_class_init (SugarCursorTrackerClass *klass)
{
    GObjectClass *object_class = G_OBJECT_CLASS (klass);
    object_class->finalize = sugar_cursor_tracker_finalize;
}

static GdkSurface *
_get_default_root_surface (void)
{
    GdkDisplay *display;
    GListModel *monitors;
    GdkMonitor *monitor;
    GdkRectangle geometry;
    GtkWindow *window;
    GdkSurface *surface = NULL;
    
    display = gdk_display_get_default ();
    if (!display)
        return NULL;

    /* Get monitors list */
    monitors = gdk_display_get_monitors (display);
    if (!monitors || g_list_model_get_n_items (monitors) == 0)
        return NULL;

    /* Get the first monitor */
    monitor = g_list_model_get_item (monitors, 0);
    if (!monitor)
        return NULL;

    /* Get the monitor geometry */
    gdk_monitor_get_geometry (monitor, &geometry);

    /* Create a new toplevel window */
	window = GTK_WINDOW(gtk_window_new());
	if (window) {
		GtkWidget *widget = GTK_WIDGET(window);
		
		/* Set window properties */
		gtk_window_set_default_size(window, geometry.width, geometry.height);
		gtk_window_set_decorated(window, FALSE);
		
		/* Position the window using GTK4 methods */
		gtk_widget_set_size_request(widget, geometry.width, geometry.height);
		
		/* Show the window */
		gtk_widget_set_visible(widget, TRUE);
		gtk_window_present(GTK_WINDOW(window));
		
		/* Get the window's surface and position it using X11 */
		surface = gtk_native_get_surface(GTK_NATIVE(window));
		if (surface) {
			Display *xdisplay = gdk_x11_display_get_xdisplay(gtk_widget_get_display(widget));
			Window xwindow = gdk_x11_surface_get_xid(surface);
			XMoveWindow(xdisplay, xwindow, geometry.x, geometry.y);
		}
		
		/* We keep a reference to the window */
		g_object_set_data_full(G_OBJECT(surface), "window",
							  window,
							  (GDestroyNotify)gtk_window_destroy);
    }

    g_object_unref(monitor);
    
    return surface;
}

static void
_set_cursor_visibility (SugarCursorTracker *tracker, gboolean visible)
{
    GdkDisplay *display;
    Display *xdisplay;
    SugarCursorTrackerPrivate *priv;
    GdkSurface *root_surface;

    priv = sugar_cursor_tracker_get_instance_private(tracker);
    root_surface = priv->root_surface;
    if (!root_surface)
        return;

    display = gdk_surface_get_display (root_surface);
    xdisplay = gdk_x11_display_get_xdisplay (display);

    gdk_x11_display_error_trap_push (display);

    if (visible == TRUE) {
        if (priv->cursor_shown == FALSE) {
            XFixesShowCursor (xdisplay,
                            gdk_x11_surface_get_xid (root_surface));
            priv->cursor_shown = TRUE;
        }
    } else {
        if (priv->cursor_shown == TRUE) {
            XFixesHideCursor (xdisplay,
                            gdk_x11_surface_get_xid (root_surface));
            priv->cursor_shown = FALSE;
        }
    }

    if (gdk_x11_display_error_trap_pop (display)) {
        g_warning ("An error occurred trying to %s the cursor",
                   visible ? "show" : "hide");
    }
}

static void
handle_touch_begin (SugarCursorTracker *tracker)
{
    _set_cursor_visibility (tracker, FALSE);
}

static void
handle_motion (SugarCursorTracker *tracker)
{
    _set_cursor_visibility (tracker, TRUE);
}

static void
handle_button_press (SugarCursorTracker *tracker)
{
    _set_cursor_visibility (tracker, TRUE);
}

static void
sugar_cursor_tracker_init (SugarCursorTracker *tracker)
{
    SugarCursorTrackerPrivate *priv;
    GdkSeat *seat;
    
    priv = sugar_cursor_tracker_get_instance_private (tracker);
    priv->root_surface = _get_default_root_surface ();
    priv->cursor_shown = TRUE;

    /* Set up event controllers for GTK4 */
    seat = gdk_display_get_default_seat (gdk_display_get_default ());
    if (seat) {
        GdkDevice *pointer = gdk_seat_get_pointer (seat);
        if (pointer) {
            GtkEventController *touch, *motion;
            GtkGesture *gesture;

            /* Touch events */
            touch = gtk_event_controller_legacy_new ();
            gtk_event_controller_set_propagation_phase (touch, GTK_PHASE_CAPTURE);
            g_signal_connect_swapped (touch, "event", G_CALLBACK (handle_touch_begin), tracker);
            
            /* Motion events */
            motion = gtk_event_controller_motion_new ();
            g_signal_connect_swapped (motion, "motion", G_CALLBACK (handle_motion), tracker);
            
            /* Button press events */
            gesture = gtk_gesture_click_new ();
            g_signal_connect_swapped (gesture, "pressed", G_CALLBACK (handle_button_press), tracker);
        }
    }
}

SugarCursorTracker *
sugar_cursor_tracker_new (void)
{
    return g_object_new (SUGAR_TYPE_CURSOR_TRACKER, NULL);
}
