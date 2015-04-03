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

enum {
  SCALE_CHANGED,
  LAST_SIGNAL
};

struct _SugarZoomControllerPriv
{
  gdouble initial_distance;
};

static guint signals[LAST_SIGNAL] = { 0 };

G_DEFINE_TYPE (SugarZoomController,
               sugar_zoom_controller,
               SUGAR_TYPE_TOUCH_CONTROLLER)

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

static void
sugar_zoom_controller_constructed (GObject *object)
{
  g_object_set (object,
                "min-touches", 2,
                "max-touches", 2,
                NULL);
}

static gboolean
_sugar_zoom_controller_get_distance (SugarZoomController *controller,
                                     gdouble             *distance)
{
  SugarZoomControllerPriv *priv;
  gint x1, y1, x2, y2;
  GList *touches;
  gdouble dx, dy;

  priv = controller->_priv;

  if (sugar_touch_controller_get_num_touches (SUGAR_TOUCH_CONTROLLER (controller)) != 2)
    return FALSE;

  touches = sugar_touch_controller_get_sequences (SUGAR_TOUCH_CONTROLLER (controller));

  sugar_touch_controller_get_coords (SUGAR_TOUCH_CONTROLLER (controller),
                                     touches->data, &x1, &y1);
  sugar_touch_controller_get_coords (SUGAR_TOUCH_CONTROLLER (controller),
                                     touches->next->data, &x2, &y2);

  dx = x1 - x2;
  dy = y1 - y2;;
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
  g_signal_emit (controller, signals[SCALE_CHANGED], 0, zoom);

  return TRUE;
}

SugarEventControllerState
sugar_zoom_controller_get_state (SugarEventController *controller)
{
  SugarZoomControllerPriv *priv;
  gint num_touches;

  priv = SUGAR_ZOOM_CONTROLLER (controller)->_priv;
  num_touches = sugar_touch_controller_get_num_touches (SUGAR_TOUCH_CONTROLLER (controller));

  if (num_touches == 2)
    return SUGAR_EVENT_CONTROLLER_STATE_RECOGNIZED;
  else if (num_touches == 1)
    return SUGAR_EVENT_CONTROLLER_STATE_COLLECTING;

  return SUGAR_EVENT_CONTROLLER_STATE_NONE;
}

static void
sugar_zoom_controller_began (SugarEventController *controller)
{
  SugarZoomControllerPriv *priv;

  priv = SUGAR_ZOOM_CONTROLLER (controller)->_priv;
  _sugar_zoom_controller_get_distance (SUGAR_ZOOM_CONTROLLER (controller),
                                       &priv->initial_distance);
  g_object_notify (G_OBJECT (controller), "state");
}

static void
sugar_zoom_controller_updated (SugarEventController *controller)
{
  _sugar_zoom_controller_check_emit (SUGAR_ZOOM_CONTROLLER (controller));
}

static void
sugar_zoom_controller_class_init (SugarZoomControllerClass *klass)
{
  SugarEventControllerClass *controller_class;
  GObjectClass *object_class;

  object_class = G_OBJECT_CLASS (klass);
  object_class->finalize = sugar_zoom_controller_finalize;
  object_class->constructed = sugar_zoom_controller_constructed;

  controller_class = SUGAR_EVENT_CONTROLLER_CLASS (klass);
  controller_class->get_state = sugar_zoom_controller_get_state;
  controller_class->began = sugar_zoom_controller_began;
  controller_class->updated = sugar_zoom_controller_updated;

  /**
   * SugarZoomController::scale-changed:
   * @controller: the object on which the signal is emitted
   * @scale: Difference with the starting zooming state
   */
  signals[SCALE_CHANGED] =
    g_signal_new ("scale-changed",
                  SUGAR_TYPE_ZOOM_CONTROLLER,
                  G_SIGNAL_RUN_FIRST,
                  G_STRUCT_OFFSET (SugarZoomControllerClass, scale_changed),
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

/**
 * sugar_zoom_controller_get_scale_delta:
 * @controller: a #SugarZoomController
 * @scale: (out) (transfer none): zoom delta
 *
 * If @controller is on state %SUGAR_EVENT_CONTROLLER_STATE_RECOGNIZED,
 * this function returns %TRUE and fills in @scale with the zooming
 * difference since the gesture was recognized (hence the starting point
 * is considered 1x).
 *
 * Returns: %TRUE if @controller is recognizing a zoom gesture
 **/
gboolean
sugar_zoom_controller_get_scale_delta (SugarZoomController *controller,
                                       gdouble             *scale)
{
  SugarZoomControllerPriv *priv;
  gdouble distance;

  g_return_val_if_fail (SUGAR_IS_ZOOM_CONTROLLER (controller), FALSE);

  if (!_sugar_zoom_controller_get_distance (controller, &distance))
    return FALSE;

  priv = controller->_priv;

  if (scale)
    *scale = distance / priv->initial_distance;

  return TRUE;
}
