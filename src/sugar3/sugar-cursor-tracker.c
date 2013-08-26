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

#include <gdk/gdkx.h>
#include <X11/extensions/XInput2.h>
#include "sugar-cursor-tracker.h"

typedef struct _SugarCursorTrackerPriv SugarCursorTrackerPriv;

struct _SugarCursorTrackerPriv
{
	GdkWindow *root_window;
        gboolean cursor_shown;
};

G_DEFINE_TYPE (SugarCursorTracker, sugar_cursor_tracker, G_TYPE_OBJECT)


static void
sugar_cursor_tracker_finalize (GObject *object)
{
	SugarCursorTrackerPriv *priv = SUGAR_CURSOR_TRACKER (object)->_priv;

	G_OBJECT_CLASS (sugar_cursor_tracker_parent_class)->finalize (object);
}

static void
sugar_cursor_tracker_class_init (SugarCursorTrackerClass *klass)
{
	GObjectClass *object_class = G_OBJECT_CLASS (klass);

	object_class->finalize = sugar_cursor_tracker_finalize;

	g_type_class_add_private (klass, sizeof (SugarCursorTrackerPriv));
}

static GdkWindow *
_get_default_root_window (void)
{
        GdkDisplay *display;
        GdkScreen *screen;

        display = gdk_display_get_default ();
        screen = gdk_display_get_default_screen (display);

        return gdk_screen_get_root_window (screen);
}

static void
_track_raw_events (GdkWindow *window)
{
        XIEventMask mask;
	guchar *evmask;
	GdkDisplay *display;

	evmask = g_new0 (guchar, XIMaskLen (XI_LASTEVENT));
	XISetMask (evmask, XI_RawTouchBegin);
	XISetMask (evmask, XI_RawTouchEnd);
	XISetMask (evmask, XI_RawTouchUpdate);
	XISetMask (evmask, XI_RawMotion);
	XISetMask (evmask, XI_RawButtonPress);

	mask.deviceid = XIAllMasterDevices;
	mask.mask_len = sizeof (evmask);
	mask.mask = evmask;

	display = gdk_window_get_display (window);
	XISelectEvents (gdk_x11_display_get_xdisplay (display),
			gdk_x11_window_get_xid (window),
			&mask, 1);
}

static void
_set_cursor_visibility (SugarCursorTracker *tracker,
			gboolean visible)
{
        GdkDisplay *display;
	Display *xdisplay;
        SugarCursorTrackerPriv *priv;

        priv = tracker->_priv;
	display = gdk_display_get_default ();
	xdisplay = GDK_DISPLAY_XDISPLAY (display);

	gdk_error_trap_push ();

	if (visible == TRUE) {
	    if (priv->cursor_shown == FALSE) {
		XFixesShowCursor (xdisplay, GDK_WINDOW_XID (_get_default_root_window ()));
		priv->cursor_shown = TRUE;
	    }
	}
	else {
	    if (priv->cursor_shown == TRUE) {
		XFixesHideCursor (xdisplay, GDK_WINDOW_XID (_get_default_root_window ()));
		priv->cursor_shown = False;
	    }
	}

	if (gdk_error_trap_pop ()) {
	    g_warning ("An error occurred trying to %s the cursor",
		       FALSE ? "show" : "hide");
	}
}

static GdkFilterReturn
filter_function (GdkXEvent *xevent,
                 GdkEvent  *gdkevent,
                 gpointer   user_data)
{
	XEvent *ev = xevent;
	XIEvent *xiev;
	SugarCursorTracker *tracker;

	if (ev->type != GenericEvent)
	        return GDK_FILTER_CONTINUE;

	tracker = user_data;

        xiev = ev->xcookie.data;

	switch (xiev->evtype) {
	case XI_RawTouchBegin:
	        _set_cursor_visibility (tracker, FALSE);
	        return GDK_FILTER_REMOVE;
	case XI_RawMotion:
	        _set_cursor_visibility (tracker, TRUE);
	        return GDK_FILTER_REMOVE;
	case XI_RawButtonPress:
	        _set_cursor_visibility (tracker, TRUE);
	        return GDK_FILTER_REMOVE;
	default:
	        return GDK_FILTER_CONTINUE;
	}
}

static void
sugar_cursor_tracker_init (SugarCursorTracker *tracker)
{
	SugarCursorTrackerPriv *priv;
	tracker->_priv = priv = G_TYPE_INSTANCE_GET_PRIVATE (tracker,
                                                             SUGAR_TYPE_CURSOR_TRACKER,
                                                             SugarCursorTrackerPriv);
        priv->root_window = _get_default_root_window ();
	priv->cursor_shown = True;

	tracker->_priv = priv = G_TYPE_INSTANCE_GET_PRIVATE (tracker,
							     SUGAR_TYPE_CURSOR_TRACKER,
							     SugarCursorTrackerPriv);
	priv->root_window = _get_default_root_window ();
	_track_raw_events (priv->root_window);
	gdk_window_add_filter (NULL, filter_function, tracker);
}

SugarCursorTracker *
sugar_cursor_tracker_new (void)
{
	return g_object_new (SUGAR_TYPE_CURSOR_TRACKER, NULL);
}
