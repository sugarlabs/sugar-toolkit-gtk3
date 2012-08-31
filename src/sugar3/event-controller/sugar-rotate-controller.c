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
#include "sugar-rotate-controller.h"

typedef struct _SugarRotateControllerPriv SugarRotateControllerPriv;
typedef struct _SugarTouch SugarTouch;

enum {
  ANGLE_CHANGED,
  LAST_SIGNAL
};

struct _SugarTouch
{
  GdkEventSequence *sequence;
  gint x;
  gint y;
  guint set : 1;
};

struct _SugarRotateControllerPriv
{
  GdkDevice *device;
  SugarTouch touches[2];
  gdouble initial_angle;
};

static guint signals[LAST_SIGNAL] = { 0 };

G_DEFINE_TYPE (SugarRotateController,
               sugar_rotate_controller,
               SUGAR_TYPE_EVENT_CONTROLLER)

static void
sugar_rotate_controller_init (SugarRotateController *controller)
{
  controller->_priv = G_TYPE_INSTANCE_GET_PRIVATE (controller,
                                                   SUGAR_TYPE_ROTATE_CONTROLLER,
                                                   SugarRotateControllerPriv);
}

static void
sugar_rotate_controller_finalize (GObject *object)
{
  G_OBJECT_CLASS (sugar_rotate_controller_parent_class)->finalize (object);
}

static SugarTouch *
_sugar_rotate_controller_find_touch (SugarRotateController *controller,
                                     GdkEventSequence      *sequence)
{
  SugarRotateControllerPriv *priv;
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
_sugar_rotate_controller_get_angle (SugarRotateController *controller,
                                    gdouble               *angle)
{
  SugarRotateControllerPriv *priv;
  gdouble dx, dy;

  priv = controller->_priv;

  if (!priv->touches[0].set || !priv->touches[1].set)
    return FALSE;

  dx = priv->touches[0].x - priv->touches[1].x;
  dy = priv->touches[0].y - priv->touches[1].y;

  *angle = atan2 (dx, dy);

  /* Invert angle */
  *angle = (2 * G_PI) - *angle;

  /* And constraint it to 0°-360° */
  *angle = fmod (*angle, 2 * G_PI);

  return TRUE;
}

static gboolean
_sugar_rotate_controller_check_emit (SugarRotateController *controller)
{
  SugarRotateControllerPriv *priv;
  gdouble angle;

  if (!_sugar_rotate_controller_get_angle (controller, &angle))
    return FALSE;

  priv = controller->_priv;

  g_signal_emit (controller, signals[ANGLE_CHANGED], 0,
                 angle, angle - priv->initial_angle);
  return TRUE;
}

static gboolean
sugar_rotate_controller_handle_event (SugarEventController *controller,
                                      GdkEvent             *event)
{
  SugarRotateControllerPriv *priv;
  GdkEventSequence *sequence;
  gboolean handled = TRUE;
  GdkDevice *device;
  SugarTouch *touch;

  priv = SUGAR_ROTATE_CONTROLLER (controller)->_priv;
  device = gdk_event_get_device (event);
  sequence = gdk_event_get_event_sequence (event);

  if (priv->device && priv->device != device)
    return FALSE;

  touch = _sugar_rotate_controller_find_touch (SUGAR_ROTATE_CONTROLLER (controller),
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
          _sugar_rotate_controller_get_angle (SUGAR_ROTATE_CONTROLLER (controller),
                                              &priv->initial_angle);
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
      else if (priv->touches[0].set || priv->touches[1].set)
        {
          g_signal_emit_by_name (G_OBJECT (controller), "finished");
          g_object_notify (G_OBJECT (controller), "state");
        }
      break;
    case GDK_TOUCH_UPDATE:
      touch->x = event->touch.x;
      touch->y = event->touch.y;
      _sugar_rotate_controller_check_emit (SUGAR_ROTATE_CONTROLLER (controller));
      break;
    default:
      handled = FALSE;
      break;
    }

  return handled;
}

SugarEventControllerState
sugar_rotate_controller_get_state (SugarEventController *controller)
{
  SugarRotateControllerPriv *priv;

  priv = SUGAR_ROTATE_CONTROLLER (controller)->_priv;

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
sugar_rotate_controller_reset (SugarEventController *controller)
{
  SugarRotateControllerPriv *priv;

  priv = SUGAR_ROTATE_CONTROLLER (controller)->_priv;

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
sugar_rotate_controller_class_init (SugarRotateControllerClass *klass)
{
  SugarEventControllerClass *controller_class;
  GObjectClass *object_class;

  object_class = G_OBJECT_CLASS (klass);
  object_class->finalize = sugar_rotate_controller_finalize;

  controller_class = SUGAR_EVENT_CONTROLLER_CLASS (klass);
  controller_class->handle_event = sugar_rotate_controller_handle_event;
  controller_class->get_state = sugar_rotate_controller_get_state;
  controller_class->reset = sugar_rotate_controller_reset;

  signals[ANGLE_CHANGED] =
    g_signal_new ("angle-changed",
                  SUGAR_TYPE_ROTATE_CONTROLLER,
                  G_SIGNAL_RUN_FIRST,
                  G_STRUCT_OFFSET (SugarRotateControllerClass, angle_changed),
                  NULL, NULL,
                  g_cclosure_marshal_generic,
                  G_TYPE_NONE, 2,
                  G_TYPE_DOUBLE, G_TYPE_DOUBLE);

  g_type_class_add_private (klass, sizeof (SugarRotateControllerPriv));
}

SugarEventController *
sugar_rotate_controller_new (void)
{
  return g_object_new (SUGAR_TYPE_ROTATE_CONTROLLER, NULL);
}

gboolean
sugar_rotate_controller_get_angle_delta (SugarRotateController *controller,
                                         gdouble               *delta)
{
  SugarRotateControllerPriv *priv;
  gdouble angle;

  g_return_val_if_fail (SUGAR_IS_ROTATE_CONTROLLER (controller), FALSE);

  if (!_sugar_rotate_controller_get_angle (controller, &angle))
    return FALSE;

  priv = controller->_priv;

  if (delta)
    *delta = angle - priv->initial_angle;

  return TRUE;
}
