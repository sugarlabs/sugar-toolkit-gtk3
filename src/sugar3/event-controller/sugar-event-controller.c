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

#include "sugar-event-controller.h"
#include "sugar-enum-types.h"

typedef struct _SugarControllerItem SugarControllerItem;
typedef struct _SugarControllerWidgetData SugarControllerWidgetData;
typedef struct _SugarEventControllerPriv SugarEventControllerPriv;

enum {
  PROP_STATE = 1,
  PROP_WIDGET
};

enum {
  BEGAN,
  UPDATED,
  ENDED,
  LAST_SIGNAL
};

struct _SugarEventControllerPriv
{
  GtkWidget *widget;
};

struct _SugarControllerItem
{
  SugarEventController *controller;
  SugarEventControllerFlags flags;
  guint notify_handler_id;
};

struct _SugarControllerWidgetData
{
  GArray *controllers;
  guint event_handler_id;
  GtkWidget *widget;
  SugarEventController *current_exclusive;
};

G_DEFINE_ABSTRACT_TYPE (SugarEventController, sugar_event_controller, G_TYPE_OBJECT)

static guint signals[LAST_SIGNAL] = { 0 };
static GQuark quark_widget_controller_data = 0;

static void
sugar_event_controller_get_property (GObject    *object,
                                     guint       prop_id,
                                     GValue     *value,
                                     GParamSpec *pspec)
{
  SugarEventControllerPriv *priv;

  priv = SUGAR_EVENT_CONTROLLER (object)->_priv;

  switch (prop_id)
    {
    case PROP_STATE:
      {
        SugarEventControllerState state;

        state = sugar_event_controller_get_state (SUGAR_EVENT_CONTROLLER (object));
        g_value_set_enum (value, state);
        break;
      }
    case PROP_WIDGET:
      g_value_set_object (value, priv->widget);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
    }
}

static void
sugar_event_controller_set_property (GObject      *object,
                                     guint         prop_id,
                                     const GValue *value,
                                     GParamSpec   *pspec)
{
  SugarEventControllerPriv *priv;

  priv = SUGAR_EVENT_CONTROLLER (object)->_priv;

  switch (prop_id)
    {
    case PROP_WIDGET:
      priv->widget = g_value_get_object (value);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
    }
}

static void
sugar_event_controller_class_init (SugarEventControllerClass *klass)
{
  GObjectClass *object_class = G_OBJECT_CLASS (klass);

  object_class->get_property = sugar_event_controller_get_property;
  object_class->set_property = sugar_event_controller_set_property;

  g_object_class_install_property (object_class,
                                   PROP_STATE,
                                   g_param_spec_enum ("state",
                                                      "State",
                                                      "Controller state",
						      SUGAR_TYPE_EVENT_CONTROLLER_STATE,
						      SUGAR_EVENT_CONTROLLER_STATE_NONE,
                                                      G_PARAM_READABLE |
                                                      G_PARAM_STATIC_NAME |
                                                      G_PARAM_STATIC_NICK |
                                                      G_PARAM_STATIC_BLURB));
  g_object_class_install_property (object_class,
                                   PROP_WIDGET,
                                   g_param_spec_object ("widget",
                                                        "Widget",
                                                        "Widget the controller is attached to",
                                                        GTK_TYPE_WIDGET,
                                                        G_PARAM_READWRITE |
                                                        G_PARAM_STATIC_NAME |
                                                        G_PARAM_STATIC_NICK |
                                                        G_PARAM_STATIC_BLURB));
  signals[BEGAN] =
    g_signal_new ("began",
                  G_TYPE_FROM_CLASS (klass),
                  G_SIGNAL_RUN_LAST,
                  G_STRUCT_OFFSET (SugarEventControllerClass, began),
                  NULL, NULL,
                  g_cclosure_marshal_VOID__VOID,
                  G_TYPE_NONE, 0);
  signals[UPDATED] =
    g_signal_new ("updated",
                  G_TYPE_FROM_CLASS (klass),
                  G_SIGNAL_RUN_LAST,
                  G_STRUCT_OFFSET (SugarEventControllerClass, updated),
                  NULL, NULL,
                  g_cclosure_marshal_VOID__VOID,
                  G_TYPE_NONE, 0);
  signals[ENDED] =
    g_signal_new ("ended",
                  G_TYPE_FROM_CLASS (klass),
                  G_SIGNAL_RUN_LAST,
                  G_STRUCT_OFFSET (SugarEventControllerClass, ended),
                  NULL, NULL,
                  g_cclosure_marshal_VOID__VOID,
                  G_TYPE_NONE, 0);

  g_type_class_add_private (object_class, sizeof (SugarEventControllerPriv));
  quark_widget_controller_data = g_quark_from_static_string ("sugar-widget-controller-data");
}

static void
sugar_event_controller_init (SugarEventController *controller)
{
  controller->_priv = G_TYPE_INSTANCE_GET_PRIVATE (controller,
                                                   SUGAR_TYPE_EVENT_CONTROLLER,
                                                   SugarEventControllerPriv);
}

static gboolean
_sugar_event_controller_widget_event (GtkWidget            *widget,
                                      GdkEvent             *event,
                                      gpointer              user_data)
{
  SugarControllerWidgetData *data;
  gboolean handled = FALSE;
  guint i;

  data = g_object_get_qdata (G_OBJECT (widget),
                             quark_widget_controller_data);

  if (!data || !data->controllers || data->controllers->len == 0)
    return FALSE;

  for (i = 0; i < data->controllers->len; i++)
    {
      SugarEventControllerState state;
      SugarControllerItem *item;

      item = &g_array_index (data->controllers, SugarControllerItem, i);

      if (data->current_exclusive &&
          data->current_exclusive != item->controller)
        continue;

      if (event->type == GDK_GRAB_BROKEN && !event->grab_broken.keyboard)
        sugar_event_controller_reset (item->controller);
      else
        {
          if (!sugar_event_controller_handle_event (item->controller, event))
            continue;

          state = sugar_event_controller_get_state (item->controller);

          /* Consider events handled once the
           * controller recognizes the action
           */
          if (state == SUGAR_EVENT_CONTROLLER_STATE_RECOGNIZED)
            handled = TRUE;
        }
    }

  return handled;
}

gboolean
sugar_event_controller_handle_event (SugarEventController *controller,
                                     GdkEvent             *event)
{
  SugarEventControllerClass *controller_class;

  g_return_val_if_fail (SUGAR_IS_EVENT_CONTROLLER (controller), FALSE);
  g_return_val_if_fail (event != NULL, FALSE);

  controller_class = SUGAR_EVENT_CONTROLLER_GET_CLASS (controller);

  if (!controller_class->handle_event)
    return FALSE;

  return controller_class->handle_event (controller, event);
}

static SugarControllerWidgetData *
_sugar_event_controller_widget_data_new (GtkWidget *widget)
{
  SugarControllerWidgetData *data;

  data = g_slice_new0 (SugarControllerWidgetData);
  data->widget = widget;
  data->controllers = g_array_new (FALSE, TRUE, sizeof (SugarControllerItem));
  data->event_handler_id =
    g_signal_connect (widget, "event",
                      G_CALLBACK (_sugar_event_controller_widget_event),
                      NULL);
  return data;
}

static void
_sugar_event_controller_widget_data_free (SugarControllerWidgetData *data)
{
  guint i;

  if (g_signal_handler_is_connected (data->widget, data->event_handler_id))
    g_signal_handler_disconnect (data->widget, data->event_handler_id);

  for (i = 0; i < data->controllers->len; i++)
    {
      SugarControllerItem *item;

      item = &g_array_index (data->controllers, SugarControllerItem, i);
      g_signal_handler_disconnect (item->controller, item->notify_handler_id);
      g_object_unref (item->controller);
    }

  g_array_unref (data->controllers);
  g_slice_free (SugarControllerWidgetData, data);
}

static void
_sugar_event_controller_state_notify (SugarEventController *controller,
                                      GParamSpec           *pspec,
                                      GtkWidget            *widget)
{
  SugarControllerWidgetData *data;
  SugarControllerItem *item, *ptr;
  SugarEventControllerState state;
  guint i;

  data = g_object_get_qdata (G_OBJECT (widget), quark_widget_controller_data);
  state = sugar_event_controller_get_state (controller);

  if (!data)
    return;

  if (state == SUGAR_EVENT_CONTROLLER_STATE_NONE &&
      data->current_exclusive == controller)
    data->current_exclusive = NULL;
  else if (!data->current_exclusive &&
           state == SUGAR_EVENT_CONTROLLER_STATE_RECOGNIZED)
    {
      for (i = 0; i < data->controllers->len; i++)
        {
          ptr = &g_array_index (data->controllers, SugarControllerItem, i);
          if (ptr->controller == controller)
            {
              item = ptr;
              break;
            }
        }

      if (!item)
        return;

      if ((item->flags & SUGAR_EVENT_CONTROLLER_FLAG_EXCLUSIVE) != 0)
        {
          data->current_exclusive = controller;

          /* Reset all other controllers */
          for (i = 0; i < data->controllers->len; i++)
            {
              ptr = &g_array_index (data->controllers, SugarControllerItem, i);

              if (ptr->controller != controller)
                sugar_event_controller_reset (ptr->controller);
            }
        }
    }
}

gboolean
sugar_event_controller_attach (SugarEventController      *controller,
                               GtkWidget                 *widget,
                               SugarEventControllerFlags  flags)
{
  SugarControllerWidgetData *data;
  SugarControllerItem *ptr, item;
  guint i;

  g_return_val_if_fail (SUGAR_IS_EVENT_CONTROLLER (controller), FALSE);
  g_return_val_if_fail (GTK_IS_WIDGET (widget), FALSE);

  data = g_object_get_qdata (G_OBJECT (widget), quark_widget_controller_data);

  if (!data)
    {
      data = _sugar_event_controller_widget_data_new (widget);
      g_object_set_qdata_full (G_OBJECT (widget),
                               quark_widget_controller_data, data,
                               (GDestroyNotify) _sugar_event_controller_widget_data_free);
    }

  for (i = 0; i < data->controllers->len; i++)
    {
      ptr = &g_array_index (data->controllers, SugarControllerItem, i);

      if (ptr->controller == controller)
        return FALSE;
    }

  item.controller = g_object_ref (controller);
  item.flags = flags;
  item.notify_handler_id = g_signal_connect (controller, "notify::state",
                                             G_CALLBACK (_sugar_event_controller_state_notify),
                                             widget);
  g_array_append_val (data->controllers, item);
  g_object_set (controller, "widget", widget, NULL);

  return TRUE;
}

gboolean
sugar_event_controller_detach (SugarEventController *controller,
                               GtkWidget            *widget)
{
  SugarControllerWidgetData *data;
  SugarControllerItem *item;
  gboolean removed = FALSE;
  guint i;

  g_return_val_if_fail (SUGAR_IS_EVENT_CONTROLLER (controller), FALSE);
  g_return_val_if_fail (GTK_IS_WIDGET (widget), FALSE);

  data = g_object_get_qdata (G_OBJECT (widget), quark_widget_controller_data);

  if (!data)
    return FALSE;

  for (i = 0; i < data->controllers->len; i++)
    {
      item = &g_array_index (data->controllers, SugarControllerItem, i);

      if (item->controller == controller)
        {
          sugar_event_controller_reset (item->controller);
          g_object_set (controller, "widget", NULL, NULL);
          g_object_unref (item->controller);
          g_signal_handler_disconnect (item->controller,
                                       item->notify_handler_id);

          g_array_remove_index_fast (data->controllers, i);
          removed = TRUE;
        }
    }

  if (data->controllers->len == 0)
    g_object_set_qdata (G_OBJECT (widget), quark_widget_controller_data, NULL);

  return removed;
}

gboolean
sugar_event_controller_reset (SugarEventController *controller)
{
  SugarEventControllerClass *controller_class;

  g_return_val_if_fail (SUGAR_IS_EVENT_CONTROLLER (controller), FALSE);

  controller_class = SUGAR_EVENT_CONTROLLER_GET_CLASS (controller);

  if (!controller_class->reset)
    return FALSE;

  controller_class->reset (controller);

  return sugar_event_controller_get_state (controller) ==
    SUGAR_EVENT_CONTROLLER_STATE_NONE;
}

SugarEventControllerState
sugar_event_controller_get_state (SugarEventController *controller)
{
  SugarEventControllerClass *controller_class;

  g_return_val_if_fail (SUGAR_IS_EVENT_CONTROLLER (controller),
                        SUGAR_EVENT_CONTROLLER_STATE_NONE);

  controller_class = SUGAR_EVENT_CONTROLLER_GET_CLASS (controller);

  if (!controller_class->get_state)
    return SUGAR_EVENT_CONTROLLER_STATE_NONE;

  return controller_class->get_state (controller);
}
