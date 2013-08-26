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

#include <gdk/gdkx.h>
#include <X11/extensions/XInput2.h>
#include "sugar-gesture-grabber.h"

typedef struct _SugarGestureGrabberPriv SugarGestureGrabberPriv;
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

struct _SugarGestureGrabberPriv
{
	GdkWindow *root_window;
	GArray *controllers;
	GArray *touches;
	guint cancel_timeout_id;
};

G_DEFINE_TYPE (SugarGestureGrabber, sugar_gesture_grabber, G_TYPE_OBJECT)

static void
_sugar_gesture_grabber_notify_touch (SugarGestureGrabber *grabber,
				     GdkDevice           *device,
				     GdkEventSequence    *sequence,
				     gboolean             handled)
{
	SugarGestureGrabberPriv *priv = grabber->_priv;
	GdkDisplay *display;
	guint i;

	display = gdk_window_get_display (priv->root_window);

	for (i = 0; i < priv->touches->len; i++) {
		TouchData *data;

		data = &g_array_index (priv->touches, TouchData, i);

		if (device && data->device != device)
			continue;

		if (sequence && data->sequence != sequence)
			continue;

		if (data->consumed)
			continue;

		gdk_error_trap_push ();
		XIAllowTouchEvents (gdk_x11_display_get_xdisplay (display),
				    gdk_x11_device_get_id (data->device),
				    GPOINTER_TO_INT (data->sequence),
				    gdk_x11_window_get_xid (priv->root_window),
				    (handled) ? XIAcceptTouch : XIRejectTouch);

		gdk_error_trap_pop_ignored ();
		data->consumed = TRUE;
	}
}

static void
_sugar_gesture_grabber_add_touch (SugarGestureGrabber *grabber,
				  GdkDevice           *device,
				  GdkEventSequence    *sequence)
{
	SugarGestureGrabberPriv *priv = grabber->_priv;
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
	SugarGestureGrabberPriv *priv = grabber->_priv;
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
	SugarGestureGrabberPriv *priv = grabber->_priv;

	_sugar_gesture_grabber_notify_touch (grabber, NULL, NULL, FALSE);
	priv->cancel_timeout_id = 0;

	return FALSE;
}

static void
sugar_gesture_grabber_finalize (GObject *object)
{
	SugarGestureGrabberPriv *priv = SUGAR_GESTURE_GRABBER (object)->_priv;
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

	g_type_class_add_private (klass, sizeof (SugarGestureGrabberPriv));
}

static void
_grab_touch_events (GdkWindow *window)
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
        display = gdk_window_get_display (window);

        XIGrabTouchBegin (gdk_x11_display_get_xdisplay (display),
                          XIAllMasterDevices,
                          gdk_x11_window_get_xid (window),
                          XINoOwnerEvents, &evmask, 1, &mods);
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

static gboolean
_sugar_gesture_grabber_run_controllers (SugarGestureGrabber *grabber,
					GdkEvent            *event)
{
	SugarGestureGrabberPriv *priv = grabber->_priv;
	gboolean handled = FALSE;
	guint i;

	for (i = 0; i < priv->controllers->len; i++) {
		ControllerData *data;

		data = &g_array_index (priv->controllers, ControllerData, i);

		if (event->type == GDK_TOUCH_BEGIN &&
                    (event->touch.x_root < data->rect.x ||
                     event->touch.x_root > data->rect.x + data->rect.width ||
                     event->touch.y_root < data->rect.y ||
                     event->touch.y_root > data->rect.y + data->rect.height))
			continue;

		handled = sugar_event_controller_handle_event (data->controller,
							       event);

		if (handled) {
			guint state;

			state = sugar_event_controller_get_state (data->controller);

			if (state == SUGAR_EVENT_CONTROLLER_STATE_RECOGNIZED) {
				_sugar_gesture_grabber_notify_touch (grabber,
								     event->touch.device,
								     event->touch.sequence,
								     TRUE);
			}
		}
	}

	return handled;
}

static GdkFilterReturn
filter_function (GdkXEvent *xevent,
                 GdkEvent  *gdkevent,
                 gpointer   user_data)
{
        XGenericEventCookie *xge = xevent;
        GdkDeviceManager *device_manager;
        SugarGestureGrabber *grabber;
        SugarGestureGrabberPriv *priv;
        gboolean handled = FALSE;
        GdkDevice *device;
        XIDeviceEvent *ev;
        GdkDisplay *display;
        GdkEvent *event;

        if (xge->type != GenericEvent)
                return GDK_FILTER_CONTINUE;

        grabber = user_data;
        priv = grabber->_priv;

        display = gdk_window_get_display (priv->root_window);
        device_manager = gdk_display_get_device_manager (display);
        ev = (XIDeviceEvent *) xge->data;

        switch (ev->evtype) {
        case XI_TouchBegin:
                event = gdk_event_new (GDK_TOUCH_BEGIN);
                break;
        case XI_TouchEnd:
                event = gdk_event_new (GDK_TOUCH_END);
                break;
        case XI_TouchUpdate:
                event = gdk_event_new (GDK_TOUCH_UPDATE);
                break;
        default:
                return GDK_FILTER_CONTINUE;
        }

        if (ev->event != gdk_x11_window_get_xid (priv->root_window))
                return GDK_FILTER_CONTINUE;

        event->touch.window = g_object_ref (priv->root_window);
        event->touch.time = ev->time;
        event->touch.x = ev->event_x;
        event->touch.y = ev->event_y;
        event->touch.x_root = ev->root_x;
        event->touch.y_root = ev->root_y;
        event->touch.sequence = GINT_TO_POINTER (ev->detail);
        event->touch.emulating_pointer = (ev->flags & XITouchEmulatingPointer);

        device = gdk_x11_device_manager_lookup (device_manager, ev->deviceid);
        gdk_event_set_device (event, device);

        device = gdk_x11_device_manager_lookup (device_manager, ev->sourceid);
        gdk_event_set_source_device (event, device);

        handled = _sugar_gesture_grabber_run_controllers (grabber, event);

        if (!handled) {
                gdk_error_trap_push ();
                XIAllowTouchEvents (gdk_x11_display_get_xdisplay (display),
                                    ev->deviceid, ev->detail,
                                    gdk_x11_window_get_xid (priv->root_window),
                                    XIRejectTouch);
                gdk_error_trap_pop_ignored ();
        } else if (event->type == GDK_TOUCH_BEGIN) {
                _sugar_gesture_grabber_add_touch (grabber,
                                                  event->touch.device,
                                                  event->touch.sequence);
        } else if (event->type == GDK_TOUCH_END) {
                _sugar_gesture_grabber_notify_touch (grabber,
                                                     event->touch.device,
                                                     event->touch.sequence,
                                                     FALSE);
                _sugar_gesture_grabber_remove_touch (grabber,
                                                     event->touch.device,
                                                     event->touch.sequence);
        }

        if (handled) {
                if (priv->cancel_timeout_id)
                        g_source_remove (priv->cancel_timeout_id);

                priv->cancel_timeout_id =
                        gdk_threads_add_timeout (150,
                                                 (GSourceFunc) _sugar_gesture_grabber_cancel_timeout,
                                                 grabber);
        }

        gdk_event_free (event);

        return GDK_FILTER_REMOVE;
}

static void
sugar_gesture_grabber_init (SugarGestureGrabber *grabber)
{
	SugarGestureGrabberPriv *priv;

	grabber->_priv = priv = G_TYPE_INSTANCE_GET_PRIVATE (grabber,
							     SUGAR_TYPE_GESTURE_GRABBER,
							     SugarGestureGrabberPriv);
	priv->root_window = _get_default_root_window ();
	_grab_touch_events (priv->root_window);
	gdk_window_add_filter (NULL, filter_function, grabber);

	priv->touches = g_array_new (FALSE, FALSE, sizeof (TouchData));
	priv->controllers = g_array_new (FALSE, FALSE, sizeof (ControllerData));
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
	SugarGestureGrabberPriv *priv;
	guint i;

	priv = grabber->_priv;

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
	SugarGestureGrabberPriv *priv;
	ControllerData data;

	g_return_if_fail (SUGAR_IS_GESTURE_GRABBER (grabber));
	g_return_if_fail (SUGAR_IS_EVENT_CONTROLLER (controller));

	if (_sugar_gesture_grabber_find_controller (grabber, controller, NULL)) {
		g_warning ("Controller is already on the gesture grabber"
			   " list. Controllers can only be added once.");
		return;
	}

	priv = grabber->_priv;

	data.controller = g_object_ref (controller);
	data.rect = *rect;
	g_array_append_val (priv->controllers, data);
}

void
sugar_gesture_grabber_remove (SugarGestureGrabber  *grabber,
			      SugarEventController *controller)
{
	SugarGestureGrabberPriv *priv;
	ControllerData *data;
	gint pos;

	g_return_if_fail (SUGAR_IS_GESTURE_GRABBER (grabber));
	g_return_if_fail (SUGAR_IS_EVENT_CONTROLLER (controller));

	priv = grabber->_priv;
	data = _sugar_gesture_grabber_find_controller (grabber, controller, &pos);

	if (data) {
		g_array_remove_index_fast (priv->controllers, pos);
		sugar_event_controller_reset (data->controller);
		g_object_unref (data->controller);
	}
}
