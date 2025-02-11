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
 * Author: Carlos Garnacho  <carlos@lanedo.com>
 */
#include <gtk/gtk.h>
#include <gdk/gdk.h>
#include <gdk/gdksurface.h>

#include <gdk/x11/gdkx.h>
#include <graphene.h>
#include <X11/extensions/XInput2.h>
#include "sugar-gesture-grabber.h"

typedef struct _ControllerData ControllerData;
typedef struct _TouchData TouchData;

struct _TouchData
{
	GdkDevice *device;
	GdkEventSequence *sequence;
	gboolean consumed;
};

struct _ControllerData
{
	SugarEventController *controller;
	GdkRectangle rect;
};

G_DEFINE_TYPE_WITH_PRIVATE (SugarGestureGrabber, sugar_gesture_grabber, G_TYPE_OBJECT)

static void handle_touch_event(GtkGesture *gesture,
	GdkEventSequence *sequence,
	gpointer user_data);


static void
_sugar_gesture_grabber_notify_touch (SugarGestureGrabber *grabber,
					GdkDevice           *device,
					GdkEventSequence    *sequence,
					gboolean             handled)
{
	SugarGestureGrabberPrivate *priv = grabber->priv;
	GdkDisplay *display;
	guint i;

	/* Use root_surface instead of root_window */
	display = gdk_surface_get_display (priv->root_surface);

	for (i = 0; i < priv->touches->len; i++) {
		TouchData *data;

		data = &g_array_index (priv->touches, TouchData, i);

		if (device && data->device != device)
			continue;

		if (sequence && data->sequence != sequence)
			continue;

		if (data->consumed)
			continue;

		gdk_x11_display_error_trap_push (display);
		XIAllowTouchEvents (gdk_x11_display_get_xdisplay (display),
					gdk_x11_device_get_id (data->device),
					GPOINTER_TO_INT (data->sequence),
					gdk_x11_surface_get_xid (priv->root_surface),
					(handled) ? XIAcceptTouch : XIRejectTouch);
		gdk_x11_display_error_trap_pop_ignored (display);
		data->consumed = TRUE;
	}
}

static void
_sugar_gesture_grabber_add_touch (SugarGestureGrabber *grabber,
				GdkDevice           *device,
				GdkEventSequence    *sequence)
{
	SugarGestureGrabberPrivate *priv = grabber->priv;
	TouchData data;

	data.device = device;
	data.sequence = sequence;
	data.consumed = FALSE;
	g_array_append_val (priv->touches, data);
}

static void
_sugar_gesture_grabber_remove_touch (SugarGestureGrabber *grabber,
					GdkDevice           *device,
					GdkEventSequence    *sequence)
{
	SugarGestureGrabberPrivate *priv = grabber->priv;
	guint i;

	for (i = 0; i < priv->touches->len; i++) {
		TouchData *data;

		data = &g_array_index (priv->touches, TouchData, i);

		if (data->device == device &&
			data->sequence == sequence) {
			g_array_remove_index_fast (priv->touches, i);
			break;
		}
	}
}

static gboolean
_sugar_gesture_grabber_cancel_timeout (SugarGestureGrabber *grabber)
{
	SugarGestureGrabberPrivate *priv = grabber->priv;

	_sugar_gesture_grabber_notify_touch (grabber, NULL, NULL, FALSE);
	priv->cancel_timeout_id = 0;

	return FALSE;
}

static void
sugar_gesture_grabber_finalize (GObject *object)
{
	SugarGestureGrabberPrivate *priv = SUGAR_GESTURE_GRABBER (object)->priv;
	guint i;

	if (priv->cancel_timeout_id) {
		g_source_remove (priv->cancel_timeout_id);
		priv->cancel_timeout_id = 0;
	}

	_sugar_gesture_grabber_notify_touch (SUGAR_GESTURE_GRABBER (object),
						NULL, NULL, FALSE);

	for (i = 0; i < priv->controllers->len; i++) {
		ControllerData *data;

		data = &g_array_index (priv->controllers, ControllerData, i);
		g_object_unref (data->controller);
	}

	g_array_free (priv->controllers, TRUE);
	g_array_free (priv->touches, TRUE);

	G_OBJECT_CLASS (sugar_gesture_grabber_parent_class)->finalize (object);
}

static void
sugar_gesture_grabber_class_init (SugarGestureGrabberClass *klass)
{
	GObjectClass *object_class = G_OBJECT_CLASS (klass);

	object_class->finalize = sugar_gesture_grabber_finalize;
}

/* Update _grab_touch_events to accept a GdkSurface instead of GdkWindow */
static void
_grab_touch_events (GdkSurface *surface)
{
		XIGrabModifiers mods = { 1 };
		unsigned char mask[4] = { 0 };
		GdkDisplay *display;
		XIEventMask evmask;

		XISetMask (mask, XI_TouchBegin);
		XISetMask (mask, XI_TouchUpdate);
		XISetMask (mask, XI_TouchEnd);

		evmask.deviceid = XIAllMasterDevices;
		evmask.mask_len = sizeof (mask);
		evmask.mask = mask;

		mods.modifiers = XIAnyModifier;
		display = gdk_surface_get_display (surface);

		XIGrabTouchBegin (gdk_x11_display_get_xdisplay (display),
						XIAllMasterDevices,
						gdk_x11_surface_get_xid (surface),
						XINoOwnerEvents, &evmask, 1, &mods);
}

static GdkSurface *
_get_default_root_surface (void)
{
    GdkDisplay *display;
    GdkSurface *surface = NULL;
    
    display = gdk_display_get_default();
    if (!display)
        return NULL;

    /* Get the default seat for the display */
    GdkSeat *seat = gdk_display_get_default_seat(display);
    if (!seat)
        return NULL;

    /* Create fullscreen window on the primary monitor */
    GtkWindow *window = GTK_WINDOW(gtk_window_new());
    if (window) {
        /* Make it fullscreen */
        gtk_window_fullscreen(window);
        gtk_window_set_decorated(window, FALSE);
        
        /* Show the window */
        gtk_widget_set_visible(GTK_WIDGET(window), TRUE);
        gtk_window_present(window);
        
        /* Get the native surface */
        surface = gtk_native_get_surface(GTK_NATIVE(window));
    }
    
    return surface;
}

static gboolean
_sugar_gesture_grabber_run_controllers (SugarGestureGrabber *grabber,
                                      GdkEvent *event)
{
    SugarGestureGrabberPrivate *priv = grabber->priv;
    gboolean handled = FALSE;
    double x, y;
    
    if (!gdk_event_get_position(event, &x, &y))
        return FALSE;

    GdkSurface *surface = gdk_event_get_surface(event);
    if (!surface)
        return FALSE;

    /* Get surface position relative to root */
    graphene_point_t pos = GRAPHENE_POINT_INIT (0, 0);
    
    /* Get the surface's position in the root coordinate system */
    GdkDisplay *display = gdk_surface_get_display(surface);
    if (display) {
        GdkMonitor *monitor = gdk_display_get_monitor_at_surface(display, surface);
        if (monitor) {
            GdkRectangle geometry;
            gdk_monitor_get_geometry(monitor, &geometry);
            pos.x = geometry.x;
            pos.y = geometry.y;
        }
    }

    double x_root = x + pos.x;
    double y_root = y + pos.y;

    for (guint i = 0; i < priv->controllers->len; i++) {
        ControllerData *data = &g_array_index(priv->controllers, ControllerData, i);

        if (gdk_event_get_event_type(event) == GDK_TOUCH_BEGIN) {
            if (x_root < data->rect.x ||
                x_root > data->rect.x + data->rect.width ||
                y_root < data->rect.y ||
                y_root > data->rect.y + data->rect.height)
                continue;
        }

        handled = sugar_event_controller_handle_event(data->controller, event);

        if (handled && 
            sugar_event_controller_get_state(data->controller) == SUGAR_EVENT_CONTROLLER_STATE_RECOGNIZED) {
            _sugar_gesture_grabber_notify_touch(grabber,
                                              gdk_event_get_device(event),
                                              gdk_event_get_event_sequence(event),
                                              TRUE);
        }
    }

    return handled;
}


static void
gesture_controller_event_cb (GtkEventController *controller,
                           GdkEvent           *event,
                           SugarGestureGrabber *grabber)
{
    SugarGestureGrabberPrivate *priv = grabber->priv;
    gboolean handled = FALSE;
    
    if (!priv->root_surface)
        return;

    handled = _sugar_gesture_grabber_run_controllers(grabber, event);

    if (!handled) {
        GdkDevice *device = gdk_event_get_device(event);
        GdkEventSequence *sequence = gdk_event_get_event_sequence(event);
        _sugar_gesture_grabber_notify_touch(grabber, device, sequence, FALSE);
    } else if (gdk_event_get_event_type(event) == GDK_TOUCH_BEGIN) {
        GdkDevice *device = gdk_event_get_device(event);
        GdkEventSequence *sequence = gdk_event_get_event_sequence(event);
        _sugar_gesture_grabber_add_touch(grabber, device, sequence);
    } else if (gdk_event_get_event_type(event) == GDK_TOUCH_END) {
        GdkDevice *device = gdk_event_get_device(event);
        GdkEventSequence *sequence = gdk_event_get_event_sequence(event);
        _sugar_gesture_grabber_notify_touch(grabber, device, sequence, FALSE);
        _sugar_gesture_grabber_remove_touch(grabber, device, sequence);
    }
}


static void
handle_touch_event (GtkGesture *gesture,
                   GdkEventSequence *sequence,
                   gpointer user_data)
{
    SugarGestureGrabber *grabber = SUGAR_GESTURE_GRABBER(user_data);
    GdkEvent *event;
    
    event = gtk_event_controller_get_current_event(GTK_EVENT_CONTROLLER(gesture));
    if (!event)
        return;
    
    gboolean handled = _sugar_gesture_grabber_run_controllers(grabber, event);
    
    if (!handled) {
        GdkDevice *device = gdk_event_get_device(event);
        GdkEventSequence *seq = gdk_event_get_event_sequence(event);
        _sugar_gesture_grabber_notify_touch(grabber, device, seq, FALSE);
    }
}

static void
sugar_gesture_grabber_init (SugarGestureGrabber *grabber)
{
    SugarGestureGrabberPrivate *priv;
    
    grabber->priv = priv = sugar_gesture_grabber_get_instance_private(grabber);
    priv->root_surface = _get_default_root_surface();
    
    if (priv->root_surface) {
        GtkWidget *widget = gtk_widget_get_ancestor(GTK_WIDGET(priv->root_surface), 
                                                  GTK_TYPE_WINDOW);
        if (widget) {
            /* Add touch gesture controller */
            GtkGesture *gesture = gtk_gesture_click_new();
            gtk_gesture_single_set_touch_only(GTK_GESTURE_SINGLE(gesture), TRUE);
            gtk_widget_add_controller(widget, GTK_EVENT_CONTROLLER(gesture));
            
            /* Connect to touch event */
            g_signal_connect(gesture, "begin",
                           G_CALLBACK(handle_touch_event), grabber);
        }
    }

    priv->touches = g_array_new(FALSE, FALSE, sizeof(TouchData));
    priv->controllers = g_array_new(FALSE, FALSE, sizeof(ControllerData));
}

SugarGestureGrabber *
sugar_gesture_grabber_new (void)
{
	return g_object_new (SUGAR_TYPE_GESTURE_GRABBER, NULL);
}

static ControllerData *
_sugar_gesture_grabber_find_controller (SugarGestureGrabber  *grabber,
					SugarEventController *controller,
					gint		     *pos)
{
	SugarGestureGrabberPrivate *priv;
	guint i;

	priv = grabber->priv;

	for (i = 0; i < priv->controllers->len; i++) {
		ControllerData *data;

		data = &g_array_index (priv->controllers, ControllerData, i);

		if (data->controller == controller) {
			if (pos)
				*pos = i;

			return data;
		}
	}

	return NULL;
}

void
sugar_gesture_grabber_add (SugarGestureGrabber  *grabber,
			SugarEventController *controller,
			const GdkRectangle   *rect)
{
	SugarGestureGrabberPrivate *priv;
	ControllerData data;

	g_return_if_fail (SUGAR_IS_GESTURE_GRABBER (grabber));
	g_return_if_fail (SUGAR_IS_EVENT_CONTROLLER (controller));

	if (_sugar_gesture_grabber_find_controller (grabber, controller, NULL)) {
		g_warning ("Controller is already on the gesture grabber"
			" list. Controllers can only be added once.");
		return;
	}

	priv = grabber->priv;

	data.controller = g_object_ref (controller);
	data.rect = *rect;
	g_array_append_val (priv->controllers, data);
}

void
sugar_gesture_grabber_remove (SugarGestureGrabber  *grabber,
				SugarEventController *controller)
{
	SugarGestureGrabberPrivate *priv;
	ControllerData *data;
	gint pos;

	g_return_if_fail (SUGAR_IS_GESTURE_GRABBER (grabber));
	g_return_if_fail (SUGAR_IS_EVENT_CONTROLLER (controller));

	priv = grabber->priv;
	data = _sugar_gesture_grabber_find_controller (grabber, controller, &pos);

	if (data) {
		g_array_remove_index_fast (priv->controllers, pos);
		sugar_event_controller_reset (data->controller);
		g_object_unref (data->controller);
	}
}
