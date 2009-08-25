/* app.c
 * Copyright (C) 2007 Novell, Inc.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
 * 02111-1307, USA.
 */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <glib.h>
#include <string.h>
#include <sys/wait.h>

#include "gsm-app.h"

enum {
  EXITED,
  REGISTERED,
  LAST_SIGNAL
};

static guint signals[LAST_SIGNAL] = { 0 };

enum {
	PROP_0,

	PROP_DESKTOP_FILE,
	PROP_CLIENT_ID,

	LAST_PROP
};

static void set_property (GObject *object, guint prop_id,
			  const GValue *value, GParamSpec *pspec);
static void get_property (GObject *object, guint prop_id,
			  GValue *value, GParamSpec *pspec);
static void dispose      (GObject *object);

static const char *get_basename (GsmApp *app);
static pid_t       launch       (GsmApp *app, GError **err);

G_DEFINE_TYPE (GsmApp, gsm_app, G_TYPE_OBJECT)

static void
gsm_app_init (GsmApp *app)
{
  app->pid = -1;
}

static void
gsm_app_class_init (GsmAppClass *app_class)
{
  GObjectClass *object_class = G_OBJECT_CLASS (app_class);

  object_class->set_property = set_property;
  object_class->get_property = get_property;
  object_class->dispose = dispose;

  app_class->get_basename = get_basename;
  app_class->launch = launch;

  g_object_class_install_property (object_class,
				   PROP_DESKTOP_FILE,
				   g_param_spec_string ("desktop-file",
							"Desktop file",
							"Freedesktop .desktop file",
							NULL,
							G_PARAM_READWRITE));
  g_object_class_install_property (object_class,
				   PROP_CLIENT_ID,
				   g_param_spec_string ("client-id",
							"Client ID",
							"Session management client ID",
							NULL,
							G_PARAM_READWRITE));

  signals[EXITED] =
    g_signal_new ("exited",
                  G_OBJECT_CLASS_TYPE (object_class),
                  G_SIGNAL_RUN_LAST,
                  G_STRUCT_OFFSET (GsmAppClass, exited),
                  NULL, NULL,
                  g_cclosure_marshal_VOID__VOID,
                  G_TYPE_NONE,
                  0);

  signals[REGISTERED] =
    g_signal_new ("registered",
                  G_OBJECT_CLASS_TYPE (object_class),
                  G_SIGNAL_RUN_LAST,
                  G_STRUCT_OFFSET (GsmAppClass, registered),
                  NULL, NULL,
                  g_cclosure_marshal_VOID__VOID,
                  G_TYPE_NONE,
                  0);
}

static void
set_property (GObject *object, guint prop_id,
	      const GValue *value, GParamSpec *pspec)
{
  GsmApp *app = GSM_APP (object);
  const char *desktop_file;
  char *phase;
  GError *error = NULL;

  switch (prop_id)
    {
    case PROP_DESKTOP_FILE:
      if (app->desktop_file)
	egg_desktop_file_free (app->desktop_file);
      desktop_file = g_value_get_string (value);
      if (!desktop_file)
	{
	  app->desktop_file = NULL;
	  break;
	}

      app->desktop_file = egg_desktop_file_new (desktop_file, &error);
      if (!app->desktop_file)
	{
	  g_warning ("Could not parse desktop file %s: %s",
		     desktop_file, error->message);
	  g_error_free (error);
	  break;
	}

      phase = egg_desktop_file_get_string (app->desktop_file,
					   "X-GNOME-Autostart-Phase", NULL);
      if (phase)
	{
	  if (!strcmp (phase, "Initialization"))
	    app->phase = GSM_SESSION_PHASE_INITIALIZATION;
	  else if (!strcmp (phase, "WindowManager"))
	    app->phase = GSM_SESSION_PHASE_WINDOW_MANAGER;
	  else if (!strcmp (phase, "Panel"))
	    app->phase = GSM_SESSION_PHASE_PANEL;
	  else if (!strcmp (phase, "Desktop"))
	    app->phase = GSM_SESSION_PHASE_DESKTOP;
	  else
	    app->phase = GSM_SESSION_PHASE_APPLICATION;

	  g_free (phase);
	}
      else
	app->phase = GSM_SESSION_PHASE_APPLICATION;
      break;

    case PROP_CLIENT_ID:
      g_free (app->client_id);
      app->client_id = g_value_dup_string (value);
      break;

    default:
      break;
    }
}

static void
get_property (GObject *object, guint prop_id,
	      GValue *value, GParamSpec *pspec)
{
  GsmApp *app = GSM_APP (object);

  switch (prop_id)
    {
    case PROP_DESKTOP_FILE:
      if (app->desktop_file)
	g_value_set_string (value, egg_desktop_file_get_source (app->desktop_file));
      else
	g_value_set_string (value, NULL);
      break;

    case PROP_CLIENT_ID:
      g_value_set_string (value, app->client_id);
      break;

    default:
      break;
    }
}

static void
dispose(GObject *object)
{
  GsmApp *app = GSM_APP (object);

  if (app->desktop_file)
    {
      egg_desktop_file_free (app->desktop_file);
      app->desktop_file = NULL;
    }

  if (app->startup_id)
    {
      g_free (app->startup_id);
      app->startup_id = NULL;
    }

  if (app->client_id)
    {
      g_free (app->client_id);
      app->client_id = NULL;
    }
}

/**
 * gsm_app_get_basename:
 * @app: a %GsmApp
 *
 * Returns an identifying name for @app, e.g. the basename of the path to
 * @app's desktop file (if any).
 *
 * Return value: an identifying name for @app, or %NULL.
 **/
const char *
gsm_app_get_basename (GsmApp *app)
{
  return GSM_APP_GET_CLASS (app)->get_basename (app);
}

static const char *
get_basename (GsmApp *app)
{
  const char *location, *slash;

  if (!app->desktop_file)
    return NULL;

  location = egg_desktop_file_get_source (app->desktop_file);

  slash = strrchr (location, '/');
  if (slash)
    return slash + 1;
  else
    return location;
}

/**
 * gsm_app_get_phase:
 * @app: a %GsmApp
 *
 * Returns @app's startup phase.
 *
 * Return value: @app's startup phase
 **/
GsmSessionPhase
gsm_app_get_phase (GsmApp *app)
{
  g_return_val_if_fail (GSM_IS_APP (app), GSM_SESSION_PHASE_APPLICATION);

  return app->phase;
}

/**
 * gsm_app_is_disabled:
 * @app: a %GsmApp
 *
 * Tests if @app is disabled
 *
 * Return value: whether or not @app is disabled
 **/
gboolean
gsm_app_is_disabled (GsmApp *app)
{
  g_return_val_if_fail (GSM_IS_APP (app), FALSE);

  if (GSM_APP_GET_CLASS (app)->is_disabled)
    return GSM_APP_GET_CLASS (app)->is_disabled (app);
  else
    return FALSE;
}

gboolean
gsm_app_provides (GsmApp *app, const char *service)
{
  char **provides;
  gsize len, i;

  g_return_val_if_fail (GSM_IS_APP (app), FALSE);

  if (!app->desktop_file)
    return FALSE;

  provides = egg_desktop_file_get_string_list (app->desktop_file,
					       "X-GNOME-Provides",
					       &len, NULL);
  if (!provides)
    return FALSE;

  for (i = 0; i < len; i++)
    {
      if (!strcmp (provides[i], service))
	{
	  g_strfreev (provides);
	  return TRUE;
	}
    }

  g_strfreev (provides);
  return FALSE;
}

static void
app_exited (GPid pid, gint status, gpointer data)
{
  if (WIFEXITED (status))
    g_signal_emit (GSM_APP (data), signals[EXITED], 0);
}

static pid_t
launch (GsmApp  *app,
	GError **err)
{
  char *env[2] = { NULL, NULL };
  gboolean success;

  g_return_val_if_fail (app->desktop_file != NULL, (pid_t)-1);

  if (egg_desktop_file_get_boolean (app->desktop_file,
				    "X-GNOME-Autostart-Notify", NULL) ||
      egg_desktop_file_get_boolean (app->desktop_file,
				    "AutostartNotify", NULL))
    env[0] = g_strdup_printf ("DESKTOP_AUTOSTART_ID=%s", app->client_id);

#if 0
  g_debug ("launching %s with client_id %s\n",
	    gsm_app_get_basename (app), app->client_id);
#endif

  success =
    egg_desktop_file_launch (app->desktop_file, NULL, err,
			     EGG_DESKTOP_FILE_LAUNCH_PUTENV, env,
			     EGG_DESKTOP_FILE_LAUNCH_FLAGS, G_SPAWN_DO_NOT_REAP_CHILD,
			     EGG_DESKTOP_FILE_LAUNCH_RETURN_PID, &app->pid,
			     EGG_DESKTOP_FILE_LAUNCH_RETURN_STARTUP_ID, &app->startup_id,
			     NULL);

  g_free (env[0]);

  if (success)
    {
      /* In case the app belongs to Initialization phase, we monitor
       * if it exits to emit proper "exited" signal to session. */
      if (app->phase == GSM_SESSION_PHASE_INITIALIZATION)
        g_child_watch_add ((GPid) app->pid, app_exited, app);

      return app->pid;
    }
  else
    return (pid_t) -1;
}

/**
 * gsm_app_launch:
 * @app: a %GsmApp
 * @err: an error pointer
 *
 * Launches @app
 *
 * Return value: the pid of the new process, or -1 on error
 **/
pid_t
gsm_app_launch (GsmApp *app, GError **err)
{
  return GSM_APP_GET_CLASS (app)->launch (app, err);
}

/**
 * gsm_app_registered:
 * @app: a %GsmApp
 *
 * Emits "registered" signal in @app
 **/
void
gsm_app_registered (GsmApp *app)
{
  g_return_if_fail (GSM_IS_APP (app));

  g_signal_emit (app, signals[REGISTERED], 0);
}

