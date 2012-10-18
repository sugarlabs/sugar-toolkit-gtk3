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

#include "sugar-touch-controller.h"
#define TOUCHES_IN_RANGE(t,p) ((t) >= (p)->min_touches && (t) <= (p)->max_touches)

typedef struct _SugarTouchControllerPriv SugarTouchControllerPriv;
typedef struct _SugarTouch SugarTouch;

enum {
  PROP_MIN_TOUCHES = 1,
  PROP_MAX_TOUCHES
};

struct _SugarTouchControllerPriv
{
  GHashTable *touches;
  gint min_touches;
  gint max_touches;
};

G_DEFINE_ABSTRACT_TYPE (SugarTouchController, sugar_touch_controller,
                        SUGAR_TYPE_EVENT_CONTROLLER)

static void
sugar_touch_controller_get_property (GObject    *object,
                                     guint       prop_id,
                                     GValue     *value,
                                     GParamSpec *pspec)
{
  SugarTouchControllerPriv *priv;

  priv = SUGAR_TOUCH_CONTROLLER (object)->_priv;

  switch (prop_id)
    {
    case PROP_MIN_TOUCHES:
      g_value_set_int (value, priv->min_touches);
      break;
    case PROP_MAX_TOUCHES:
      g_value_set_int (value, priv->max_touches);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
    }
}

static void
sugar_touch_controller_set_property (GObject      *object,
                                     guint         prop_id,
                                     const GValue *value,
                                     GParamSpec   *pspec)
{
  SugarTouchControllerPriv *priv;

  priv = SUGAR_TOUCH_CONTROLLER (object)->_priv;

  switch (prop_id)
    {
    case PROP_MIN_TOUCHES:
      priv->min_touches = g_value_get_int (value);
      break;
    case PROP_MAX_TOUCHES:
      priv->max_touches = g_value_get_int (value);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
    }
}

static void
sugar_touch_controller_finalize (GObject *object)
{
  SugarTouchControllerPriv *priv;

  priv = SUGAR_TOUCH_CONTROLLER (object)->_priv;
  g_hash_table_destroy (priv->touches);

  G_OBJECT_CLASS (sugar_touch_controller_parent_class)->finalize (object);
}

static gboolean
sugar_touch_controller_handle_event (SugarEventController *controller,
                                     GdkEvent             *event)
{
  SugarTouchControllerPriv *priv;
  GdkEventSequence *sequence;
  gboolean handled = TRUE;
  GdkPoint *point;
  gint n_touches, prev_n_touches;
  gboolean is_in_range, was_in_range;

  priv = SUGAR_TOUCH_CONTROLLER (controller)->_priv;
  sequence = gdk_event_get_event_sequence (event);
  prev_n_touches = g_hash_table_size (priv->touches);
  was_in_range = TOUCHES_IN_RANGE (prev_n_touches, priv);

  if (!sequence)
    return FALSE;

  switch (event->type)
    {
    case GDK_TOUCH_BEGIN:
      point = g_new0 (GdkPoint, 1);
      point->x = event->touch.x;
      point->y = event->touch.y;
      g_hash_table_insert (priv->touches, sequence, point);
      break;
    case GDK_TOUCH_END:
      g_hash_table_remove (priv->touches, sequence);
      break;
    case GDK_TOUCH_UPDATE:
      point = g_hash_table_lookup (priv->touches, sequence);

      if (point)
        {
          point->x = event->touch.x;
          point->y = event->touch.y;
        }
      else
        handled = FALSE;
      break;
    default:
      handled = FALSE;
    }

  n_touches = g_hash_table_size (priv->touches);
  is_in_range = TOUCHES_IN_RANGE (n_touches, priv);

  if (handled)
    {
      if (is_in_range)
        {
          if (!was_in_range)
            g_signal_emit_by_name (controller, "began");
          else
            g_signal_emit_by_name (controller, "updated");
        }
      else if (was_in_range)
        g_signal_emit_by_name (controller, "ended");
    }

  return handled;
}

static void
sugar_touch_controller_reset (SugarEventController *controller)
{
  SugarTouchControllerPriv *priv;
  gint n_touches;

  priv = SUGAR_TOUCH_CONTROLLER (controller)->_priv;
  n_touches = g_hash_table_size (priv->touches);

  if (TOUCHES_IN_RANGE (n_touches, priv))
    g_signal_emit_by_name (G_OBJECT (controller), "ended");

  g_hash_table_remove_all (priv->touches);
  g_object_notify (G_OBJECT (controller), "state");
}

static void
sugar_touch_controller_class_init (SugarTouchControllerClass *klass)
{
  SugarEventControllerClass *controller_class = SUGAR_EVENT_CONTROLLER_CLASS (klass);
  GObjectClass *object_class = G_OBJECT_CLASS (klass);

  controller_class->handle_event = sugar_touch_controller_handle_event;
  controller_class->reset = sugar_touch_controller_reset;

  object_class->get_property = sugar_touch_controller_get_property;
  object_class->set_property = sugar_touch_controller_set_property;
  object_class->finalize = sugar_touch_controller_finalize;

  g_object_class_install_property (object_class,
                                   PROP_MIN_TOUCHES,
                                   g_param_spec_int ("min-touches",
                                                     "Minimum number of touches",
                                                     "Minimum Number of touches",
                                                     1, G_MAXINT, 1,
                                                     G_PARAM_CONSTRUCT |
                                                     G_PARAM_READWRITE |
                                                     G_PARAM_STATIC_NAME |
                                                     G_PARAM_STATIC_NICK |
                                                     G_PARAM_STATIC_BLURB));
  g_object_class_install_property (object_class,
                                   PROP_MAX_TOUCHES,
                                   g_param_spec_int ("max-touches",
                                                     "Maximum number of touches",
                                                     "Maximum Number of touches",
                                                     1, G_MAXINT, 1,
                                                     G_PARAM_CONSTRUCT |
                                                     G_PARAM_READWRITE |
                                                     G_PARAM_STATIC_NAME |
                                                     G_PARAM_STATIC_NICK |
                                                     G_PARAM_STATIC_BLURB));

  g_type_class_add_private (object_class, sizeof (SugarTouchControllerPriv));
}

static void
sugar_touch_controller_init (SugarTouchController *controller)
{
  SugarTouchControllerPriv *priv;
  controller->_priv = priv = G_TYPE_INSTANCE_GET_PRIVATE (controller,
                                                          SUGAR_TYPE_TOUCH_CONTROLLER,
                                                          SugarTouchControllerPriv);
  priv->touches = g_hash_table_new_full (NULL, NULL, NULL,
                                         (GDestroyNotify) g_free);
}

/**
 * sugar_touch_controller_get_center:
 * @controller: a #SugarTouchController
 * @center_x: (out) (transfer none): Return location for the X axis of the bounding box center
 * @center_y: (out) (transfer none): Return location for the Y axis of the bounding box center
 *
 * If a gesture is ongoing, this function returns the center of
 * the bounding box containing all ongoing touches.
 *
 * Returns: %TRUE if a gesture is in progress
 **/
gboolean
sugar_touch_controller_get_center (SugarTouchController *controller,
                                   gint                 *center_x,
                                   gint                 *center_y)
{
  SugarTouchControllerPriv *priv;
  GHashTableIter iter;
  GdkPoint *point;
  gint x1, y1, x2, y2, dx, dy;

  g_return_val_if_fail (SUGAR_IS_TOUCH_CONTROLLER (controller), FALSE);

  priv = controller->_priv;
  x1 = y1 = G_MAXINT;
  x2 = y2 = G_MININT;

  if (!TOUCHES_IN_RANGE (g_hash_table_size (priv->touches), priv))
    return FALSE;

  g_hash_table_iter_init (&iter, priv->touches);

  while (g_hash_table_iter_next (&iter, NULL, (gpointer *) &point))
    {
      x1 = MIN (x1, point->x);
      y1 = MIN (y1, point->y);
      x2 = MAX (x2, point->x);
      y2 = MAX (y2, point->y);
    }

  if (center_x)
    {
      dx = x2 - x1;
      *center_x = x1 + (ABS (dx) / 2);
    }

  if (center_y)
    {
      dy = y2 - y1;
      *center_y = y1 + (ABS (dy) / 2);
    }

  return TRUE;
}

/**
 * sugar_touch_controller_get_num_touches:
 * @controller: a #SugarTouchController
 *
 * Returns the number of touches currently operating on @controller
 *
 * Returns: The number of touches
 **/
gint
sugar_touch_controller_get_num_touches (SugarTouchController *controller)
{
  SugarTouchControllerPriv *priv;

  g_return_val_if_fail (SUGAR_IS_TOUCH_CONTROLLER (controller), 0);

  priv = controller->_priv;

  return g_hash_table_size (priv->touches);
}

/**
 * sugar_touch_controller_get_sequences:
 * @controller: a #SugarTouchController
 *
 * Returns the touch sequences currently operating on @controller
 *
 * Returns: (element-type Gdk.EventSequence) (transfer container): The list of sequences
 **/
GList *
sugar_touch_controller_get_sequences (SugarTouchController *controller)
{
  SugarTouchControllerPriv *priv;

  g_return_val_if_fail (SUGAR_IS_TOUCH_CONTROLLER (controller), NULL);

  priv = controller->_priv;

  return g_hash_table_get_keys (priv->touches);
}

/**
 * sugar_touch_controller_get_coords:
 * @controller: a #SugarTouchController
 * @sequence: a #GdkEventSequence
 * @x: (out) (transfer none): Return location for the X coordinate of the touch
 * @y: (out) (transfer none): Return location for the X coordinate of the touch
 *
 * If @sequence is operating on @controller, this function returns %TRUE and
 * fills in @x and @y with the latest coordinates for that @sequence.
 *
 * Returns: %TRUE if @sequence operates on @controller
 **/
gboolean
sugar_touch_controller_get_coords (SugarTouchController *controller,
                                   GdkEventSequence     *sequence,
                                   gint                 *x,
                                   gint                 *y)
{
  SugarTouchControllerPriv *priv;
  GdkPoint *point;

  g_return_val_if_fail (SUGAR_IS_TOUCH_CONTROLLER (controller), FALSE);
  g_return_val_if_fail (sequence != NULL, FALSE);

  priv = controller->_priv;
  point = g_hash_table_lookup (priv->touches, sequence);

  if (!point)
    return FALSE;

  if (x)
    *x = point->x;

  if (y)
    *y = point->y;

  return TRUE;
}
