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

#define DEFAULT_THRESHOLD 32
#define DEFAULT_TIMEOUT   800
#define ANIM_WINDOW_WIDTH 100
#define ARC_LINE_WIDTH    10

typedef struct _SugarLongPressControllerPriv SugarLongPressControllerPriv;

enum {
  PROP_0,
  PROP_THRESHOLD,
  PROP_TIMEOUT
};

struct _SugarLongPressControllerPriv
{
  GdkDevice *device;
  GdkEventSequence *sequence;
  GtkWidget *anim_window;
  gint64 start_time;
  gint x;
  gint y;
  gint root_x;
  gint root_y;
  guint anim_id;
  guint timeout_id;
  guint threshold;
  guint timeout;
  guint cancelled : 1;
  guint triggered : 1;
};

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
  priv->timeout = DEFAULT_TIMEOUT;
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

  if (priv->anim_id)
    {
      g_source_remove (priv->anim_id);
      priv->anim_id = 0;
    }

  if (priv->anim_window &&
      gtk_widget_get_visible (priv->anim_window))
    gtk_widget_hide (priv->anim_window);

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
    case PROP_TIMEOUT:
      g_value_set_uint (value, priv->timeout);
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
    case PROP_TIMEOUT:
      priv->timeout = g_value_get_uint (value);
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

static void
_stroke_progress_notification (cairo_t *cr,
                               gdouble  progress)
{
  cairo_set_line_width (cr, ARC_LINE_WIDTH);
  cairo_arc (cr,
             ANIM_WINDOW_WIDTH / 2,
             ANIM_WINDOW_WIDTH / 2,
             ANIM_WINDOW_WIDTH / 2 - ARC_LINE_WIDTH / 2,
             - G_PI_2, (2 * G_PI * progress) - G_PI_2);
  cairo_stroke (cr);
}

static gboolean
_sugar_long_press_anim_draw (GtkWidget                *widget,
                             cairo_t                  *cr,
                             SugarLongPressController *controller)
{
  SugarLongPressControllerPriv *priv = controller->_priv;
  gdouble progress;
  gint64 diff_msec;

  diff_msec = (g_get_monotonic_time () - priv->start_time) / 1000;
  progress = (gdouble) diff_msec / priv->timeout;

  cairo_save (cr);
  cairo_set_operator (cr, CAIRO_OPERATOR_SOURCE);
  cairo_set_source_rgba (cr, 0, 0, 0, 0);
  cairo_paint (cr);
  cairo_restore (cr);

  _stroke_progress_notification (cr, progress);

  return TRUE;
}

static void
_sugar_long_press_controller_update_shape (GtkWidget                *widget,
                                           SugarLongPressController *controller)
{
  cairo_surface_t *surface;
  cairo_region_t *region;
  cairo_t *cr;

  surface = cairo_image_surface_create (CAIRO_FORMAT_A1,
                                        ANIM_WINDOW_WIDTH,
                                        ANIM_WINDOW_WIDTH);
  cr = cairo_create (surface);
  _stroke_progress_notification (cr, 1.0);
  cairo_destroy (cr);

  region = gdk_cairo_region_create_from_surface (surface);
  cairo_surface_destroy (surface);

  gtk_widget_shape_combine_region (widget, region);
  cairo_region_destroy (region);
}

static gboolean
_sugar_long_press_anim_timeout (gpointer user_data)
{
  SugarLongPressController *controller = user_data;
  SugarLongPressControllerPriv *priv = controller->_priv;
  GtkWidget *widget;

  g_object_get (controller, "widget", &widget, NULL);

  if (!widget)
    {
      priv->anim_id = 0;
      return FALSE;
    }

  if (priv->anim_window &&
      gtk_widget_get_screen (widget) !=
      gtk_widget_get_screen (priv->anim_window))
    {
      gtk_widget_destroy (priv->anim_window);
      priv->anim_window = NULL;
    }

  if (!priv->anim_window)
    {
      GdkScreen *screen;
      GdkVisual *rgba_visual;

      priv->anim_window = gtk_window_new (GTK_WINDOW_POPUP);
      gtk_widget_set_app_paintable (priv->anim_window, TRUE);
      gtk_widget_input_shape_combine_region (priv->anim_window, NULL);
      gtk_window_set_type_hint (GTK_WINDOW (priv->anim_window),
                                GDK_WINDOW_TYPE_HINT_UTILITY);

      screen = gtk_widget_get_screen (widget);
      rgba_visual = gdk_screen_get_rgba_visual (screen);

      gtk_window_set_screen (GTK_WINDOW (priv->anim_window), screen);

      if (rgba_visual)
        {
          GdkRGBA bg = { 0, 0, 0, 0 };

          gtk_widget_set_visual (priv->anim_window, rgba_visual);
          gtk_widget_override_background_color (priv->anim_window, 0, &bg);
        }
      else
        _sugar_long_press_controller_update_shape (priv->anim_window,
                                                   controller);
      g_signal_connect (priv->anim_window, "draw",
                        G_CALLBACK (_sugar_long_press_anim_draw),
                        controller);
    }

  if (!gtk_widget_get_visible (priv->anim_window))
    {
      gtk_window_move (GTK_WINDOW (priv->anim_window),
                       priv->root_x - (ANIM_WINDOW_WIDTH / 2),
                       priv->root_y - (ANIM_WINDOW_WIDTH / 2));
      gtk_window_resize (GTK_WINDOW (priv->anim_window),
                         ANIM_WINDOW_WIDTH, ANIM_WINDOW_WIDTH);
      gtk_widget_show (priv->anim_window);

      priv->anim_id =
        gdk_threads_add_timeout (20, _sugar_long_press_anim_timeout,
                                 controller);
      return FALSE;
    }
  else
    {
      gtk_widget_queue_draw (priv->anim_window);
      return TRUE;
    }
}

static gboolean
_sugar_long_press_controller_timeout (gpointer user_data)
{
  SugarLongPressController *controller = user_data;
  SugarLongPressControllerPriv *priv = controller->_priv;

  priv->timeout_id = 0;
  priv->triggered = TRUE;
  g_signal_emit_by_name (controller, "started");

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
    g_signal_emit_by_name (controller, "finished");

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

      priv->anim_id =
        gdk_threads_add_timeout (100,
                                 _sugar_long_press_anim_timeout,
                                 controller);
      priv->timeout_id =
        gdk_threads_add_timeout (priv->timeout,
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
                                   PROP_TIMEOUT,
                                   g_param_spec_uint ("timeout",
                                                      "Timeout",
                                                      "Value in milliseconds to timeout the triggering",
                                                      0, G_MAXUINT, DEFAULT_TIMEOUT,
                                                      G_PARAM_READWRITE |
                                                      G_PARAM_STATIC_NAME |
                                                      G_PARAM_STATIC_NICK |
                                                      G_PARAM_STATIC_BLURB));

  g_type_class_add_private (klass, sizeof (SugarLongPressControllerPriv));
}

SugarEventController *
sugar_long_press_controller_new (void)
{
  return g_object_new (SUGAR_TYPE_LONG_PRESS_CONTROLLER, NULL);
}
