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

#include "sugar-long-press-controller.h"

#define DEFAULT_THRESHOLD     32
#define DEFAULT_TRIGGER_DELAY 600

typedef struct _SugarLongPressControllerPriv SugarLongPressControllerPriv;

enum {
  PROP_0,
  PROP_THRESHOLD,
  PROP_TRIGGER_DELAY
};

enum {
  PRESSED,
  N_SIGNALS
};

struct _SugarLongPressControllerPriv
{
  GdkDevice *device;
  GdkEventSequence *sequence;
  gint64 start_time;
  gint x;
  gint y;
  gint root_x;
  gint root_y;
  guint timeout_id;
  guint threshold;
  guint delay;
  guint cancelled : 1;
  guint triggered : 1;
};

static guint signals[N_SIGNALS] = { 0 };

G_DEFINE_TYPE (SugarLongPressController,
               sugar_long_press_controller,
               SUGAR_TYPE_EVENT_CONTROLLER)

static void
sugar_long_press_controller_init (SugarLongPressController *controller)
{
  SugarLongPressControllerPriv *priv;

  controller->_priv = priv = G_TYPE_INSTANCE_GET_PRIVATE (controller,
                                                          SUGAR_TYPE_LONG_PRESS_CONTROLLER,
                                                          SugarLongPressControllerPriv);
  priv->threshold = DEFAULT_THRESHOLD;
  priv->delay = DEFAULT_TRIGGER_DELAY;
  priv->x = priv->y = -1;
  priv->root_x = priv->root_y = -1;
}

static void
_sugar_long_press_controller_unset_device (SugarLongPressController *controller)
{
  SugarLongPressControllerPriv *priv = controller->_priv;

  if (priv->device)
    {
      g_object_unref (priv->device);
      priv->device = NULL;
    }

  priv->sequence = NULL;
  priv->x = priv->y = -1;
  priv->root_x = priv->root_y = -1;
  priv->cancelled = priv->triggered = FALSE;
}

static gboolean
_sugar_long_press_controller_cancel (SugarLongPressController *controller)
{
  SugarLongPressControllerPriv *priv = controller->_priv;

  if (priv->timeout_id)
    {
      g_source_remove (priv->timeout_id);
      priv->timeout_id = 0;
      priv->cancelled = TRUE;
      g_object_notify (G_OBJECT (controller), "state");

      return TRUE;
    }

  return FALSE;
}

static void
sugar_long_press_controller_get_property (GObject    *object,
                                          guint       prop_id,
                                          GValue     *value,
                                          GParamSpec *pspec)
{
  SugarLongPressControllerPriv *priv = SUGAR_LONG_PRESS_CONTROLLER (object)->_priv;

  switch (prop_id)
    {
    case PROP_THRESHOLD:
      g_value_set_uint (value, priv->threshold);
      break;
    case PROP_TRIGGER_DELAY:
      g_value_set_uint (value, priv->delay);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
      break;
    }
}

static void
sugar_long_press_controller_set_property (GObject      *object,
                                          guint         prop_id,
                                          const GValue *value,
                                          GParamSpec   *pspec)
{
  SugarLongPressControllerPriv *priv = SUGAR_LONG_PRESS_CONTROLLER (object)->_priv;

  switch (prop_id)
    {
    case PROP_THRESHOLD:
      priv->threshold = g_value_get_uint (value);
      break;
    case PROP_TRIGGER_DELAY:
      priv->delay = g_value_get_uint (value);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
      break;
    }
}

static void
sugar_long_press_controller_finalize (GObject *object)
{
  SugarLongPressController *controller = SUGAR_LONG_PRESS_CONTROLLER (object);

  _sugar_long_press_controller_cancel (controller);
  _sugar_long_press_controller_unset_device (controller);

  G_OBJECT_CLASS (sugar_long_press_controller_parent_class)->finalize (object);
}

static gboolean
_sugar_long_press_controller_timeout (gpointer user_data)
{
  SugarLongPressController *controller = user_data;
  SugarLongPressControllerPriv *priv = controller->_priv;

  priv->timeout_id = 0;
  priv->triggered = TRUE;
  g_signal_emit_by_name (controller, "began");

  g_signal_emit (controller, signals[PRESSED], 0, priv->x, priv->y);

  return FALSE;
}

static SugarEventControllerState
sugar_long_press_controller_get_state (SugarEventController *controller)
{
  SugarLongPressControllerPriv *priv;

  priv = SUGAR_LONG_PRESS_CONTROLLER (controller)->_priv;

  if (priv->device)
    {
      if (priv->timeout_id)
        return SUGAR_EVENT_CONTROLLER_STATE_COLLECTING;
      else if (priv->cancelled)
        return SUGAR_EVENT_CONTROLLER_STATE_NOT_RECOGNIZED;
      else if (priv->triggered)
        return SUGAR_EVENT_CONTROLLER_STATE_RECOGNIZED;
    }

  return SUGAR_EVENT_CONTROLLER_STATE_NONE;
}

static void
sugar_long_press_controller_reset (SugarEventController *controller)
{
  SugarLongPressControllerPriv *priv;

  priv = SUGAR_LONG_PRESS_CONTROLLER (controller)->_priv;

  if (priv->triggered)
    g_signal_emit_by_name (controller, "ended");

  _sugar_long_press_controller_cancel (SUGAR_LONG_PRESS_CONTROLLER (controller));
  _sugar_long_press_controller_unset_device (SUGAR_LONG_PRESS_CONTROLLER (controller));
  g_object_notify (G_OBJECT (controller), "state");
}

static gboolean
sugar_long_press_controller_handle_event (SugarEventController *controller,
                                          GdkEvent             *event)
{
  SugarLongPressControllerPriv *priv;
  GdkEventSequence *sequence;
  gboolean handled = TRUE;
  GdkDevice *device;

  priv = SUGAR_LONG_PRESS_CONTROLLER (controller)->_priv;
  device = gdk_event_get_device (event);
  sequence = gdk_event_get_event_sequence (event);

  if (priv->device)
    {
      if (priv->device != device)
        return FALSE;

      if (sequence && priv->sequence != sequence)
        {
          /* Another touch is simultaneously operating,
           * give up on recognizing a long press.
           */
          _sugar_long_press_controller_cancel (SUGAR_LONG_PRESS_CONTROLLER (controller));

          return FALSE;
        }
    }

  switch (event->type)
    {
    case GDK_TOUCH_BEGIN:
      priv->device = g_object_ref (device);
      priv->start_time = g_get_monotonic_time ();
      priv->x = event->touch.x;
      priv->y = event->touch.y;
      priv->root_x = event->touch.x_root;
      priv->root_y = event->touch.y_root;
      priv->sequence = sequence;

      priv->timeout_id =
        gdk_threads_add_timeout (priv->delay,
                                 _sugar_long_press_controller_timeout,
                                 controller);
      g_object_notify (G_OBJECT (controller), "state");
      break;
    case GDK_TOUCH_UPDATE:
      if (ABS (priv->x - event->touch.x) > priv->threshold ||
          ABS (priv->y - event->touch.y) > priv->threshold)
        _sugar_long_press_controller_cancel (SUGAR_LONG_PRESS_CONTROLLER (controller));
      break;
    case GDK_TOUCH_END:
      sugar_event_controller_reset (controller);
      break;
    default:
      handled = FALSE;
      break;
    }

  return handled;
}

static void
sugar_long_press_controller_class_init (SugarLongPressControllerClass *klass)
{
  SugarEventControllerClass *controller_class;
  GObjectClass *object_class;

  object_class = G_OBJECT_CLASS (klass);
  object_class->get_property = sugar_long_press_controller_get_property;
  object_class->set_property = sugar_long_press_controller_set_property;
  object_class->finalize = sugar_long_press_controller_finalize;

  controller_class = SUGAR_EVENT_CONTROLLER_CLASS (klass);
  controller_class->handle_event = sugar_long_press_controller_handle_event;
  controller_class->get_state = sugar_long_press_controller_get_state;
  controller_class->reset = sugar_long_press_controller_reset;

  g_object_class_install_property (object_class,
                                   PROP_THRESHOLD,
                                   g_param_spec_uint ("threshold",
                                                      "Threshold",
                                                      "Threshold in pixels where the long "
                                                      "press operation remains valid",
                                                      0, G_MAXUINT, DEFAULT_THRESHOLD,
                                                      G_PARAM_READWRITE |
                                                      G_PARAM_STATIC_NAME |
                                                      G_PARAM_STATIC_NICK |
                                                      G_PARAM_STATIC_BLURB));
  g_object_class_install_property (object_class,
                                   PROP_TRIGGER_DELAY,
                                   g_param_spec_uint ("trigger-delay",
                                                      "Trigger delay",
                                                      "delay in milliseconds before the gesture is triggered",
                                                      0, G_MAXUINT, DEFAULT_TRIGGER_DELAY,
                                                      G_PARAM_READWRITE |
                                                      G_PARAM_STATIC_NAME |
                                                      G_PARAM_STATIC_NICK |
                                                      G_PARAM_STATIC_BLURB));
  signals[PRESSED] =
    g_signal_new ("pressed",
                  G_TYPE_FROM_CLASS (klass),
                  G_SIGNAL_RUN_LAST,
                  G_STRUCT_OFFSET (SugarLongPressControllerClass, pressed),
                  NULL, NULL,
                  g_cclosure_marshal_generic,
                  G_TYPE_NONE, 2,
                  G_TYPE_INT, G_TYPE_INT);

  g_type_class_add_private (klass, sizeof (SugarLongPressControllerPriv));
}

SugarEventController *
sugar_long_press_controller_new (void)
{
  return g_object_new (SUGAR_TYPE_LONG_PRESS_CONTROLLER, NULL);
}
