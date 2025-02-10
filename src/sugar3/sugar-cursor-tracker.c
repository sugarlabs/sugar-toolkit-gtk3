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

#include <gdk/x11/gdkx.h>
#include <gdk/gdk.h>
#include <X11/extensions/XInput2.h>
#include "sugar-cursor-tracker.h"

G_DEFINE_TYPE_WITH_PRIVATE (SugarCursorTracker, sugar_cursor_tracker, G_TYPE_OBJECT)

static void
sugar_cursor_tracker_finalize (GObject *object)
{
	SugarCursorTrackerPrivate *priv = SUGAR_CURSOR_TRACKER (object)->priv;

	G_OBJECT_CLASS (sugar_cursor_tracker_parent_class)->finalize (object);
}

static void
sugar_cursor_tracker_class_init (SugarCursorTrackerClass *klass)
{
	GObjectClass *object_class = G_OBJECT_CLASS (klass);

	object_class->finalize = sugar_cursor_tracker_finalize;
}

/* In GTK4, we use GdkSurface instead of GdkWindow */
static GdkSurface *
_get_default_root_surface (void)
{
		GdkDisplay *display;
		display = gdk_display_get_default ();
		return gdk_display_get_default_surface (display);
}

static void
_track_raw_events (GdkSurface *surface)
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
	mask.mask_len = XIMaskLen (XI_LASTEVENT);
	mask.mask = evmask;

	display = gdk_surface_get_display (surface);
	XISelectEvents (gdk_x11_display_get_xdisplay (display),
			gdk_x11_surface_get_xid (surface),
			&mask, 1);

	g_free (evmask);
}

static void
_set_cursor_visibility (SugarCursorTracker *tracker,
			gboolean visible)
{
		GdkDisplay *display;
	Display *xdisplay;
		SugarCursorTrackerPrivate *priv;

		priv = tracker->priv;
	display = gdk_display_get_default ();
	xdisplay = gdk_x11_display_get_xdisplay (display);

	gdk_x11_display_error_trap_push (display);

	if (visible == TRUE) {
		if (priv->cursor_shown == FALSE) {
		XFixesShowCursor (xdisplay, gdk_x11_surface_get_xid (_get_default_root_surface ()));
		priv->cursor_shown = TRUE;
		}
	}
	else {
		if (priv->cursor_shown == TRUE) {
		XFixesHideCursor (xdisplay, gdk_x11_surface_get_xid (_get_default_root_surface ()));
		priv->cursor_shown = FALSE;
		}
	}

	if (gdk_x11_display_error_trap_pop (display)) {
		g_warning ("An error occurred trying to %s the cursor",
			visible ? "show" : "hide");
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
	SugarCursorTrackerPrivate *priv;
	tracker->priv = priv = sugar_cursor_tracker_get_instance_private (tracker);

		priv->root_surface = _get_default_root_surface ();
	priv->cursor_shown = TRUE;

	_track_raw_events (priv->root_surface);
	/* Instead of gdk_window_add_filter, attach filter on the display */
	gdk_display_add_filter (gdk_display_get_default (), filter_function, tracker);
}

SugarCursorTracker *
sugar_cursor_tracker_new (void)
{
	return g_object_new (SUGAR_TYPE_CURSOR_TRACKER, NULL);
}
