/*
 * Copyright (C) 2012, One Laptop Per Child.
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
 * Author(s): Carlos Garnacho <carlos@lanedo.com>
 */

#include <math.h>
#include "sugar-zoom-controller.h"

typedef struct _SugarZoomControllerPriv SugarZoomControllerPriv;
typedef struct _SugarTouch SugarTouch;

enum {
  ZOOM_CHANGED,
  LAST_SIGNAL
};

struct _SugarTouch
{
  GdkEventSequence *sequence;
  gint x;
  gint y;
  guint set : 1;
};

struct _SugarZoomControllerPriv
{
  GdkDevice *device;
  SugarTouch touches[2];
  gdouble initial_distance;
};

static guint signals[LAST_SIGNAL] = { 0 };

G_DEFINE_TYPE (SugarZoomController,
               sugar_zoom_controller,
               SUGAR_TYPE_EVENT_CONTROLLER)

static void
sugar_zoom_controller_init (SugarZoomController *controller)
{
  controller->_priv = G_TYPE_INSTANCE_GET_PRIVATE (controller,
                                                   SUGAR_TYPE_ZOOM_CONTROLLER,
                                                   SugarZoomControllerPriv);
}

static void
sugar_zoom_controller_finalize (GObject *object)
{
  G_OBJECT_CLASS (sugar_zoom_controller_parent_class)->finalize (object);
}

static SugarTouch *
_sugar_zoom_controller_find_touch (SugarZoomController *controller,
                                   GdkEventSequence    *sequence)
{
  SugarZoomControllerPriv *priv;
  gint unset = -1, i;

  priv = controller->_priv;

  for (i = 0; i < 2; i++)
    {
      if (priv->touches[i].sequence == sequence)
        return &priv->touches[i];
      else if (!priv->touches[i].set && unset < 0)
        unset = i;
    }

  if (unset < 0)
    return NULL;

  priv->touches[unset].sequence = sequence;
  priv->touches[unset].set = TRUE;
  return &priv->touches[unset];
}

static gboolean
_sugar_zoom_controller_get_distance (SugarZoomController *controller,
                                     gdouble             *distance)
{
  SugarZoomControllerPriv *priv;
  gdouble dx, dy;

  priv = controller->_priv;

  if (!priv->touches[0].set || !priv->touches[1].set)
    return FALSE;

  dx = priv->touches[0].x - priv->touches[1].x;
  dy = priv->touches[0].y - priv->touches[1].y;
  *distance = sqrt ((dx * dx) + (dy * dy));

  return TRUE;
}

static gboolean
_sugar_zoom_controller_check_emit (SugarZoomController *controller)
{
  SugarZoomControllerPriv *priv;
  gdouble distance, zoom;

  if (!_sugar_zoom_controller_get_distance (controller, &distance))
    return FALSE;

  priv = controller->_priv;

  if (distance == 0 || priv->initial_distance == 0)
    return FALSE;

  zoom = distance / priv->initial_distance;
  g_signal_emit (controller, signals[ZOOM_CHANGED], 0, zoom);

  return TRUE;
}

static gboolean
sugar_zoom_controller_handle_event (SugarEventController *controller,
                                    GdkEvent             *event)
{
  SugarZoomControllerPriv *priv;
  GdkEventSequence *sequence;
  gboolean handled = TRUE;
  GdkDevice *device;
  SugarTouch *touch;

  priv = SUGAR_ZOOM_CONTROLLER (controller)->_priv;
  device = gdk_event_get_device (event);
  sequence = gdk_event_get_event_sequence (event);

  if (priv->device && priv->device != device)
    return FALSE;

  touch = _sugar_zoom_controller_find_touch (SUGAR_ZOOM_CONTROLLER (controller),
                                             sequence);
  if (!touch)
    return FALSE;

  switch (event->type)
    {
    case GDK_TOUCH_BEGIN:
      touch->x = event->touch.x;
      touch->y = event->touch.y;

      if (!priv->device)
        priv->device = g_object_ref (device);

      if (priv->touches[0].set && priv->touches[1].set)
        {
          _sugar_zoom_controller_get_distance (SUGAR_ZOOM_CONTROLLER (controller),
                                               &priv->initial_distance);
          g_signal_emit_by_name (G_OBJECT (controller), "started");
          g_object_notify (G_OBJECT (controller), "state");
        }
      break;
    case GDK_TOUCH_END:
      touch->sequence = NULL;
      touch->set = FALSE;

      if (!priv->touches[0].set && !priv->touches[1].set)
        {
          g_object_unref (priv->device);
          priv->device = NULL;
        }
      else if (!priv->touches[0].set || priv->touches[1].set)
        {
          g_signal_emit_by_name (G_OBJECT (controller), "finished");
          g_object_notify (G_OBJECT (controller), "state");
        }
      break;
    case GDK_TOUCH_UPDATE:
      touch->x = event->touch.x;
      touch->y = event->touch.y;
      _sugar_zoom_controller_check_emit (SUGAR_ZOOM_CONTROLLER (controller));
      break;
    default:
      handled = FALSE;
      break;
    }

  return handled;
}

SugarEventControllerState
sugar_zoom_controller_get_state (SugarEventController *controller)
{
  SugarZoomControllerPriv *priv;

  priv = SUGAR_ZOOM_CONTROLLER (controller)->_priv;

  if (priv->device)
    {
      if (priv->touches[0].set && priv->touches[1].set)
        return SUGAR_EVENT_CONTROLLER_STATE_RECOGNIZED;
      else if (priv->touches[0].set || priv->touches[1].set)
        return SUGAR_EVENT_CONTROLLER_STATE_COLLECTING;
    }

  return SUGAR_EVENT_CONTROLLER_STATE_NONE;
}

void
sugar_zoom_controller_reset (SugarEventController *controller)
{
  SugarZoomControllerPriv *priv;

  priv = SUGAR_ZOOM_CONTROLLER (controller)->_priv;

  if (priv->touches[0].set && priv->touches[1].set)
    g_signal_emit_by_name (G_OBJECT (controller), "finished");

  priv->touches[0].sequence = NULL;
  priv->touches[0].set = FALSE;
  priv->touches[1].sequence = NULL;
  priv->touches[1].set = FALSE;

  if (priv->device)
    {
      g_object_unref (priv->device);
      priv->device = NULL;
    }

  g_object_notify (G_OBJECT (controller), "state");
}

static void
sugar_zoom_controller_class_init (SugarZoomControllerClass *klass)
{
  SugarEventControllerClass *controller_class;
  GObjectClass *object_class;

  object_class = G_OBJECT_CLASS (klass);
  object_class->finalize = sugar_zoom_controller_finalize;

  controller_class = SUGAR_EVENT_CONTROLLER_CLASS (klass);
  controller_class->handle_event = sugar_zoom_controller_handle_event;
  controller_class->get_state = sugar_zoom_controller_get_state;
  controller_class->reset = sugar_zoom_controller_reset;

  signals[ZOOM_CHANGED] =
    g_signal_new ("zoom-changed",
                  SUGAR_TYPE_ZOOM_CONTROLLER,
                  G_SIGNAL_RUN_FIRST,
                  G_STRUCT_OFFSET (SugarZoomControllerClass, zoom_changed),
                  NULL, NULL,
                  g_cclosure_marshal_VOID__DOUBLE,
                  G_TYPE_NONE, 1,
                  G_TYPE_DOUBLE);

  g_type_class_add_private (klass, sizeof (SugarZoomControllerPriv));
}

SugarEventController *
sugar_zoom_controller_new (void)
{
  return g_object_new (SUGAR_TYPE_ZOOM_CONTROLLER, NULL);
}

gboolean
sugar_zoom_controller_get_zoom_delta (SugarZoomController *controller,
                                      gdouble             *delta)
{
  SugarZoomControllerPriv *priv;
  gdouble distance;

  g_return_val_if_fail (SUGAR_IS_ZOOM_CONTROLLER (controller), FALSE);

  if (!_sugar_zoom_controller_get_distance (controller, &distance))
    return FALSE;

  priv = controller->_priv;

  if (delta)
    *delta = distance / priv->initial_distance;

  return TRUE;
}
