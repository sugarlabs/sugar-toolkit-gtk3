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

#include "sugar-swipe-controller.h"
#include "sugar-enum-types.h"

#define CHECK_TIME 100
#define SWIPE_PX_THRESHOLD 80
#define PROPORTION_FACTOR_THRESHOLD 4

typedef struct _SugarSwipeControllerPriv SugarSwipeControllerPriv;
typedef struct _SugarEventData SugarEventData;

enum {
  PROP_DIRECTIONS = 1
};

enum {
  SWIPE_ENDED,
  LAST_SIGNAL
};

struct _SugarEventData
{
  gint x;
  gint y;
  guint32 time;
};

struct _SugarSwipeControllerPriv
{
  GdkDevice *device;
  GdkEventSequence *sequence;
  GArray *event_data;
  guint swiping : 1;
  guint swiped : 1;
  guint directions : 4;
};

static guint signals[LAST_SIGNAL] = { 0 };

G_DEFINE_TYPE (SugarSwipeController,
               sugar_swipe_controller,
               SUGAR_TYPE_EVENT_CONTROLLER)

static void
sugar_swipe_controller_init (SugarSwipeController *controller)
{
  SugarSwipeControllerPriv *priv;

  controller->_priv = priv = G_TYPE_INSTANCE_GET_PRIVATE (controller,
                                                          SUGAR_TYPE_SWIPE_CONTROLLER,
                                                          SugarSwipeControllerPriv);
  priv->event_data = g_array_new (FALSE, FALSE, sizeof (SugarEventData));
}

static void
sugar_swipe_controller_get_property (GObject    *object,
                                     guint       prop_id,
                                     GValue     *value,
                                     GParamSpec *pspec)
{
  SugarSwipeControllerPriv *priv = SUGAR_SWIPE_CONTROLLER (object)->_priv;

  switch (prop_id)
    {
    case PROP_DIRECTIONS:
      g_value_set_flags (value, priv->directions);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
    }
}

static void
sugar_swipe_controller_set_property (GObject      *object,
                                     guint         prop_id,
                                     const GValue *value,
                                     GParamSpec   *pspec)
{
  SugarSwipeControllerPriv *priv = SUGAR_SWIPE_CONTROLLER (object)->_priv;

  switch (prop_id)
    {
    case PROP_DIRECTIONS:
      priv->directions = g_value_get_flags (value);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
    }
}

static void
sugar_swipe_controller_finalize (GObject *object)
{
  G_OBJECT_CLASS (sugar_swipe_controller_parent_class)->finalize (object);
}

static void
_sugar_swipe_controller_clear_events (SugarSwipeController *controller)
{
  SugarSwipeControllerPriv *priv;

  priv = controller->_priv;

  if (priv->event_data &&
      priv->event_data->len > 0)
    g_array_remove_range (priv->event_data, 0, priv->event_data->len);

  priv->swiping = FALSE;
  priv->swiped = FALSE;
}

static void
_sugar_swipe_controller_store_event (SugarSwipeController *controller,
                                     GdkEvent             *event)
{
  SugarSwipeControllerPriv *priv;
  SugarEventData data;
  gdouble x, y;
  guint32 time;
  guint i;

  priv = controller->_priv;

  if (!gdk_event_get_coords (event, &x, &y))
    return;

  time = gdk_event_get_time (event);

  /* Remove event data older than CHECK_TIME, won't
   * be used for calculations.
   */
  for (i = 0; i < priv->event_data->len; i++)
    {
      SugarEventData *ptr;

      ptr = &g_array_index (priv->event_data, SugarEventData, i);

      if (ptr->time > time - CHECK_TIME)
        break;
    }

  if (i > 0)
    g_array_remove_range (priv->event_data, 0, i);


  /* And insert current event data */
  data.x = x;
  data.y = y;
  data.time = time;
  g_array_append_val (priv->event_data, data);
}

static gboolean
_sugar_swipe_controller_get_direction (SugarEventData      *from,
                                       SugarEventData      *to,
                                       SugarSwipeDirection *direction)
{
  gdouble dx, dy;

  if (!from || !to)
    return FALSE;

  dx = to->x - from->x;
  dy = to->y - from->y;

  if (ABS (dx) > SWIPE_PX_THRESHOLD &&
      ABS (dx) > ABS (dy) * PROPORTION_FACTOR_THRESHOLD)
    {
      if (dx < 0)
        *direction = SUGAR_SWIPE_DIRECTION_LEFT;
      else
        *direction = SUGAR_SWIPE_DIRECTION_RIGHT;

      return TRUE;
    }
  else if (ABS (dy) > SWIPE_PX_THRESHOLD &&
           ABS (dy) > ABS (dx) * PROPORTION_FACTOR_THRESHOLD)
    {
      if (dy < 0)
        *direction = SUGAR_SWIPE_DIRECTION_UP;
      else
        *direction = SUGAR_SWIPE_DIRECTION_DOWN;

      return TRUE;
    }

  return FALSE;
}

static gboolean
_sugar_swipe_controller_get_event_direction (SugarSwipeController *controller,
                                             SugarSwipeDirection  *direction)
{
  SugarSwipeControllerPriv *priv;
  SugarEventData *last, *check;
  SugarSwipeDirection dir;
  gint i;

  priv = controller->_priv;

  if (!priv->event_data || priv->event_data->len == 0)
    return FALSE;

  last = &g_array_index (priv->event_data, SugarEventData,
                         priv->event_data->len - 1);

  for (i = priv->event_data->len - 1; i >= 0; i--)
    {
      check = &g_array_index (priv->event_data, SugarEventData, i);

      if (check->time < last->time - CHECK_TIME)
        break;
    }

  if (!_sugar_swipe_controller_get_direction (check, last, &dir))
    return FALSE;

  /* Check whether the direction is allowed */
  if ((priv->directions & (1 << dir)) == 0)
    return FALSE;

  if (direction)
    *direction = dir;

  return TRUE;
}

static void
_sugar_swipe_controller_check_emit (SugarSwipeController *controller)
{
  SugarSwipeControllerPriv *priv;
  SugarSwipeDirection direction;

  priv = controller->_priv;

  if (!priv->swiping)
    return;

  if (_sugar_swipe_controller_get_event_direction (controller, &direction))
    {
      priv->swiped = TRUE;
      g_signal_emit (controller, signals[SWIPE_ENDED], 0, direction);
    }

  g_signal_emit_by_name (G_OBJECT (controller), "ended");
}

static gboolean
sugar_swipe_controller_handle_event (SugarEventController *controller,
                                     GdkEvent             *event)
{
  SugarSwipeControllerPriv *priv;
  SugarSwipeController *swipe;
  SugarSwipeDirection direction;
  GdkEventSequence *sequence;
  gboolean handled = TRUE;
  GdkDevice *device;

  device = gdk_event_get_device (event);
  sequence = gdk_event_get_event_sequence (event);

  if (!device || !sequence)
    return FALSE;

  swipe = SUGAR_SWIPE_CONTROLLER (controller);
  priv = swipe->_priv;

  if ((priv->device && priv->device != device) ||
      (priv->sequence && priv->sequence != sequence))
    return FALSE;

  switch (event->type)
    {
    case GDK_TOUCH_BEGIN:
      priv->device = g_object_ref (device);
      priv->sequence = sequence;
      _sugar_swipe_controller_clear_events (swipe);
      _sugar_swipe_controller_store_event (swipe, event);
      g_object_notify (G_OBJECT (controller), "state");
      break;
    case GDK_TOUCH_END:
      if (priv->device)
        g_object_unref (priv->device);
      priv->device = NULL;
      priv->sequence = NULL;
      _sugar_swipe_controller_store_event (swipe, event);
      _sugar_swipe_controller_check_emit (swipe);
      _sugar_swipe_controller_clear_events (swipe);
      g_object_notify (G_OBJECT (controller), "state");
      break;
    case GDK_TOUCH_UPDATE:
      _sugar_swipe_controller_store_event (swipe, event);

      if (_sugar_swipe_controller_get_event_direction (swipe, &direction))
        {
          priv->swiping = TRUE;
          g_signal_emit_by_name (G_OBJECT (controller), "began");
          g_object_notify (G_OBJECT (controller), "state");
        }
      break;
    default:
      handled = FALSE;
      break;
    }

  return handled;
}

SugarEventControllerState
sugar_swipe_controller_get_state (SugarEventController *controller)
{
  SugarSwipeControllerPriv *priv;

  priv = SUGAR_SWIPE_CONTROLLER (controller)->_priv;

  if (priv->device)
    {
      if (priv->swiped || priv->swiping)
        return SUGAR_EVENT_CONTROLLER_STATE_RECOGNIZED;
      else if (priv->event_data->len > 0)
        return SUGAR_EVENT_CONTROLLER_STATE_COLLECTING;
    }

  return SUGAR_EVENT_CONTROLLER_STATE_NONE;
}

void
sugar_swipe_controller_reset (SugarEventController *controller)
{
  SugarSwipeControllerPriv *priv;
  SugarSwipeController *swipe;

  swipe = SUGAR_SWIPE_CONTROLLER (controller);
  priv = swipe->_priv;

  if (priv->device)
    {
      g_object_unref (priv->device);
      priv->device = NULL;
    }

  _sugar_swipe_controller_clear_events (swipe);
  g_object_notify (G_OBJECT (controller), "state");
}

static void
sugar_swipe_controller_class_init (SugarSwipeControllerClass *klass)
{
  SugarEventControllerClass *controller_class;
  GObjectClass *object_class;

  object_class = G_OBJECT_CLASS (klass);
  object_class->get_property = sugar_swipe_controller_get_property;
  object_class->set_property = sugar_swipe_controller_set_property;
  object_class->finalize = sugar_swipe_controller_finalize;

  controller_class = SUGAR_EVENT_CONTROLLER_CLASS (klass);
  controller_class->handle_event = sugar_swipe_controller_handle_event;
  controller_class->get_state = sugar_swipe_controller_get_state;
  controller_class->reset = sugar_swipe_controller_reset;

  g_object_class_install_property (object_class,
                                   PROP_DIRECTIONS,
                                   g_param_spec_flags ("directions",
                                                       "Directions",
                                                       "Allowed swipe directions",
                                                       SUGAR_TYPE_SWIPE_DIRECTION_FLAGS, 0,
                                                       G_PARAM_READABLE |
                                                       G_PARAM_WRITABLE |
                                                       G_PARAM_CONSTRUCT_ONLY));
  signals[SWIPE_ENDED] =
    g_signal_new ("swipe-ended",
                  SUGAR_TYPE_SWIPE_CONTROLLER,
                  G_SIGNAL_RUN_FIRST,
                  G_STRUCT_OFFSET (SugarSwipeControllerClass, swipe_ended),
                  NULL, NULL,
                  g_cclosure_marshal_VOID__ENUM,
                  G_TYPE_NONE, 1,
                  SUGAR_TYPE_SWIPE_DIRECTION);

  g_type_class_add_private (klass, sizeof (SugarSwipeControllerPriv));
}

SugarEventController *
sugar_swipe_controller_new (SugarSwipeDirectionFlags directions)
{
  return g_object_new (SUGAR_TYPE_SWIPE_CONTROLLER,
                       "directions", directions,
                       NULL);
}
