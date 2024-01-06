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

enum {
  ANGLE_CHANGED,
  LAST_SIGNAL
};

static guint signals[LAST_SIGNAL] = { 0 };

G_DEFINE_TYPE_WITH_PRIVATE (SugarRotateController,
                            sugar_rotate_controller,
                            SUGAR_TYPE_TOUCH_CONTROLLER)

static void
sugar_rotate_controller_init (SugarRotateController *controller)
{
  controller->priv = sugar_rotate_controller_get_instance_private (controller);
}

static void
sugar_rotate_controller_finalize (GObject *object)
{
  G_OBJECT_CLASS (sugar_rotate_controller_parent_class)->finalize (object);
}

static void
sugar_rotate_controller_constructed (GObject *object)
{
  g_object_set (object,
                "min-touches", 2,
                "max-touches", 2,
                NULL);
}

static gboolean
_sugar_rotate_controller_get_angle (SugarRotateController *controller,
                                    gdouble               *angle)
{
  SugarRotateControllerPrivate *priv;
  gint x1, y1, x2, y2;
  gdouble dx, dy;
  GList *touches;

  priv = controller->priv;

  if (sugar_touch_controller_get_num_touches (SUGAR_TOUCH_CONTROLLER (controller)) != 2)
    return FALSE;

  touches = sugar_touch_controller_get_sequences (SUGAR_TOUCH_CONTROLLER (controller));

  sugar_touch_controller_get_coords (SUGAR_TOUCH_CONTROLLER (controller),
                                     touches->data, &x1, &y1);
  sugar_touch_controller_get_coords (SUGAR_TOUCH_CONTROLLER (controller),
                                     touches->next->data, &x2, &y2);

  dx = x1 - x2;
  dy = y1 - y2;

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
  SugarRotateControllerPrivate *priv;
  gdouble angle;

  if (!_sugar_rotate_controller_get_angle (controller, &angle))
    return FALSE;

  priv = controller->priv;

  g_signal_emit (controller, signals[ANGLE_CHANGED], 0,
                 angle, angle - priv->initial_angle);
  return TRUE;
}

SugarEventControllerState
sugar_rotate_controller_get_state (SugarEventController *controller)
{
  SugarRotateControllerPrivate *priv;
  gint num_touches;

  priv = SUGAR_ROTATE_CONTROLLER (controller)->priv;
  num_touches = sugar_touch_controller_get_num_touches (SUGAR_TOUCH_CONTROLLER (controller));

  if (num_touches == 2)
    return SUGAR_EVENT_CONTROLLER_STATE_RECOGNIZED;
  else if (num_touches == 1)
    return SUGAR_EVENT_CONTROLLER_STATE_COLLECTING;

  return SUGAR_EVENT_CONTROLLER_STATE_NONE;
}

void
sugar_rotate_controller_began (SugarEventController *controller)
{
  SugarRotateControllerPrivate *priv;

  priv = SUGAR_ROTATE_CONTROLLER (controller)->priv;
  _sugar_rotate_controller_get_angle (SUGAR_ROTATE_CONTROLLER (controller),
                                      &priv->initial_angle);
  g_object_notify (G_OBJECT (controller), "state");
}

void
sugar_rotate_controller_updated (SugarEventController *controller)
{
  _sugar_rotate_controller_check_emit (SUGAR_ROTATE_CONTROLLER (controller));
}

static void
sugar_rotate_controller_class_init (SugarRotateControllerClass *klass)
{
  SugarEventControllerClass *controller_class;
  GObjectClass *object_class;

  object_class = G_OBJECT_CLASS (klass);
  object_class->finalize = sugar_rotate_controller_finalize;
  object_class->constructed = sugar_rotate_controller_constructed;

  controller_class = SUGAR_EVENT_CONTROLLER_CLASS (klass);
  controller_class->get_state = sugar_rotate_controller_get_state;
  controller_class->began = sugar_rotate_controller_began;
  controller_class->updated = sugar_rotate_controller_updated;

  /**
   * SugarRotateController::angle-changed:
   * @controller: the object on which the signal is emitted
   * @angle: Current angle in radians
   * @angle_delta: Difference with the starting angle in radians
   */
  signals[ANGLE_CHANGED] =
    g_signal_new ("angle-changed",
                  SUGAR_TYPE_ROTATE_CONTROLLER,
                  G_SIGNAL_RUN_FIRST,
                  G_STRUCT_OFFSET (SugarRotateControllerClass, angle_changed),
                  NULL, NULL,
                  g_cclosure_marshal_generic,
                  G_TYPE_NONE, 2,
                  G_TYPE_DOUBLE, G_TYPE_DOUBLE);
}

SugarEventController *
sugar_rotate_controller_new (void)
{
  return g_object_new (SUGAR_TYPE_ROTATE_CONTROLLER, NULL);
}

/**
 * sugar_rotate_controller_get_angle_delta:
 * @controller: a #SugarRotateController
 * @delta: (out) (transfer none): angle delta
 *
 * If @controller is on state %SUGAR_EVENT_CONTROLLER_STATE_RECOGNIZED,
 * this function returns %TRUE and fills in @delta with the angle difference
 * in radians since the gesture was first recognized.
 *
 * Returns: %TRUE if @controller is recognizing a rotate gesture
 **/
gboolean
sugar_rotate_controller_get_angle_delta (SugarRotateController *controller,
                                         gdouble               *delta)
{
  SugarRotateControllerPrivate *priv;
  gdouble angle;

  g_return_val_if_fail (SUGAR_IS_ROTATE_CONTROLLER (controller), FALSE);

  if (!_sugar_rotate_controller_get_angle (controller, &angle))
    return FALSE;

  priv = controller->priv;

  if (delta)
    *delta = angle - priv->initial_angle;

  return TRUE;
}
