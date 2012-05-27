/*
 * Copyright (C) 2007 Novell, Inc.
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Library General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Library General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <string.h>
#include <glib/gi18n.h>

#include "eggsmclient.h"
#include "eggsmclient-private.h"

static void egg_sm_client_debug_handler (const char *log_domain,
					 GLogLevelFlags log_level,
					 const char *message,
					 gpointer user_data);

enum {
  SAVE_STATE,
  QUIT_REQUESTED,
  QUIT_CANCELLED,
  QUIT,
  LAST_SIGNAL
};

static guint signals[LAST_SIGNAL] = { 0 };

struct _EggSMClientPrivate {
  GKeyFile *state_file;
};

#define EGG_SM_CLIENT_GET_PRIVATE(o) (G_TYPE_INSTANCE_GET_PRIVATE ((o), EGG_TYPE_SM_CLIENT, EggSMClientPrivate))

G_DEFINE_TYPE (EggSMClient, egg_sm_client, G_TYPE_OBJECT)

static void
egg_sm_client_init (EggSMClient *client)
{
}

static void
egg_sm_client_class_init (EggSMClientClass *klass)
{
  GObjectClass *object_class = G_OBJECT_CLASS (klass);

  g_type_class_add_private (klass, sizeof (EggSMClientPrivate));

  /**
   * EggSMClient::save_state:
   * @client: the client
   * @state_file: a #GKeyFile to save state information into
   *
   * Emitted when the session manager has requested that the
   * application save information about its current state. The
   * application should save its state into @state_file, and then the
   * session manager may then restart the application in a future
   * session and tell it to initialize itself from that state.
   *
   * You should not save any data into @state_file's "start group"
   * (ie, the %NULL group). Instead, applications should save their
   * data into groups with names that start with the application name,
   * and libraries that connect to this signal should save their data
   * into groups with names that start with the library name.
   *
   * Alternatively, rather than (or in addition to) using @state_file,
   * the application can save its state by calling
   * egg_sm_client_set_restart_command() during the processing of this
   * signal (eg, to include a list of files to open).
   **/
  signals[SAVE_STATE] =
    g_signal_new ("save_state",
                  G_OBJECT_CLASS_TYPE (object_class),
                  G_SIGNAL_RUN_LAST,
                  G_STRUCT_OFFSET (EggSMClientClass, save_state),
                  NULL, NULL,
                  g_cclosure_marshal_VOID__POINTER,
                  G_TYPE_NONE,
                  1, G_TYPE_POINTER);

  /**
   * EggSMClient::quit_requested:
   * @client: the client
   *
   * Emitted when the session manager requests that the application
   * exit (generally because the user is logging out). The application
   * should decide whether or not it is willing to quit (perhaps after
   * asking the user what to do with documents that have unsaved
   * changes) and then call egg_sm_client_will_quit(), passing %TRUE
   * or %FALSE to give its answer to the session manager. (It does not
   * need to give an answer before returning from the signal handler;
   * it can interact with the user asynchronously and then give its
   * answer later on.) If the application does not connect to this
   * signal, then #EggSMClient will automatically return %TRUE on its
   * behalf.
   *
   * The application should not save its session state as part of
   * handling this signal; if the user has requested that the session
   * be saved when logging out, then ::save_state will be emitted
   * separately.
   *
   * If the application agrees to quit, it should then wait for either
   * the ::quit_cancelled or ::quit signals to be emitted.
   **/
  signals[QUIT_REQUESTED] =
    g_signal_new ("quit_requested",
                  G_OBJECT_CLASS_TYPE (object_class),
                  G_SIGNAL_RUN_LAST,
                  G_STRUCT_OFFSET (EggSMClientClass, quit_requested),
                  NULL, NULL,
                  g_cclosure_marshal_VOID__VOID,
                  G_TYPE_NONE,
                  0);

  /**
   * EggSMClient::quit_cancelled:
   * @client: the client
   *
   * Emitted when the session manager decides to cancel a logout after
   * the application has already agreed to quit. After receiving this
   * signal, the application can go back to what it was doing before
   * receiving the ::quit_requested signal.
   **/
  signals[QUIT_CANCELLED] =
    g_signal_new ("quit_cancelled",
                  G_OBJECT_CLASS_TYPE (object_class),
                  G_SIGNAL_RUN_LAST,
                  G_STRUCT_OFFSET (EggSMClientClass, quit_cancelled),
                  NULL, NULL,
                  g_cclosure_marshal_VOID__VOID,
                  G_TYPE_NONE,
                  0);

  /**
   * EggSMClient::quit:
   * @client: the client
   *
   * Emitted when the session manager wants the application to quit
   * (generally because the user is logging out). The application
   * should exit as soon as possible after receiving this signal; if
   * it does not, the session manager may choose to forcibly kill it.
   *
   * Normally a GUI application would only be sent a ::quit if it
   * agreed to quit in response to a ::quit_requested signal. However,
   * this is not guaranteed; in some situations the session manager
   * may decide to end the session without giving applications a
   * chance to object.
   **/
  signals[QUIT] =
    g_signal_new ("quit",
                  G_OBJECT_CLASS_TYPE (object_class),
                  G_SIGNAL_RUN_LAST,
                  G_STRUCT_OFFSET (EggSMClientClass, quit),
                  NULL, NULL,
                  g_cclosure_marshal_VOID__VOID,
                  G_TYPE_NONE,
                  0);
}

static gboolean sm_client_disable = FALSE;
static char *sm_client_state_file = NULL;
static char *sm_client_id = NULL;

static GOptionEntry entries[] = {
  { "sm-client-disable", 0, 0,
    G_OPTION_ARG_NONE, &sm_client_disable,
    N_("Disable connection to session manager"), NULL },
  { "sm-client-state-file", 0, 0,
    G_OPTION_ARG_STRING, &sm_client_state_file,
    N_("Specify file containing saved configuration"), N_("FILE") },
  { "sm-client-id", 0, 0,
    G_OPTION_ARG_STRING, &sm_client_id,
    N_("Specify session management ID"), N_("ID") },
  { NULL }
};

/**
 * egg_sm_client_is_resumed:
 * @client: the client
 *
 * Checks whether or not the current session has been resumed from
 * a previous saved session. If so, the application should call
 * egg_sm_client_get_state_file() and restore its state from the
 * returned #GKeyFile.
 *
 * Return value: %TRUE if the session has been resumed
 **/
gboolean
egg_sm_client_is_resumed (EggSMClient *client)
{
  return sm_client_state_file != NULL;
}

/**
 * egg_sm_client_get_state_file:
 * @client: the client
 *
 * If the application was resumed by the session manager, this will
 * return the #GKeyFile containing its state from the previous
 * session.
 *
 * Note that other libraries and #EggSMClient itself may also store
 * state in the key file, so if you call egg_sm_client_get_groups(),
 * on it, the return value will likely include groups that you did not
 * put there yourself. (It is also not guaranteed that the first
 * group created by the application will still be the "start group"
 * when it is resumed.)
 *
 * Return value: the #GKeyFile containing the application's earlier
 * state, or %NULL on error. You should not free this key file; it
 * is owned by @client.
 **/
GKeyFile *
egg_sm_client_get_state_file (EggSMClient *client)
{
  EggSMClientPrivate *priv = EGG_SM_CLIENT_GET_PRIVATE (client);
  char *state_file_path;
  GError *err = NULL;

  if (!sm_client_state_file)
    return NULL;
  if (priv->state_file)
    return priv->state_file;

  if (!strncmp (sm_client_state_file, "file://", 7))
    state_file_path = g_filename_from_uri (sm_client_state_file, NULL, NULL);
  else
    state_file_path = g_strdup (sm_client_state_file);

  priv->state_file = g_key_file_new ();
  if (!g_key_file_load_from_file (priv->state_file, state_file_path, 0, &err))
    {
      g_warning ("Could not load SM state file '%s': %s",
		 sm_client_state_file, err->message);
      g_clear_error (&err);
      g_key_file_free (priv->state_file);
      priv->state_file = NULL;
    }

  g_free (state_file_path);
  return priv->state_file;
}

/**
 * egg_sm_client_set_restart_command:
 * @client: the client
 * @argc: the length of @argv
 * @argv: argument vector
 *
 * Sets the command used to restart @client if it does not have a
 * .desktop file that can be used to find its restart command.
 *
 * This can also be used when handling the ::save_state signal, to
 * save the current state via an updated command line. (Eg, providing
 * a list of filenames to open when the application is resumed.)
 **/
void
egg_sm_client_set_restart_command (EggSMClient  *client,
				   int           argc,
				   const char  **argv)
{
  g_return_if_fail (EGG_IS_SM_CLIENT (client));

  if (EGG_SM_CLIENT_GET_CLASS (client)->set_restart_command)
    EGG_SM_CLIENT_GET_CLASS (client)->set_restart_command (client, argc, argv);
}

/**
 * egg_sm_client_will_quit:
 * @client: the client
 * @will_quit: whether or not the application is willing to quit
 *
 * This MUST be called in response to the ::quit_requested signal, to
 * indicate whether or not the application is willing to quit. The
 * application may call it either directly from the signal handler, or
 * at some later point (eg, after asynchronously interacting with the
 * user).
 *
 * If the application does not connect to ::quit_requested,
 * #EggSMClient will call this method on its behalf (passing %TRUE
 * for @will_quit).
 *
 * After calling this method, the application should wait to receive
 * either ::quit_cancelled or ::quit.
 **/
void
egg_sm_client_will_quit (EggSMClient *client,
			 gboolean     will_quit)
{
  g_return_if_fail (EGG_IS_SM_CLIENT (client));

  if (EGG_SM_CLIENT_GET_CLASS (client)->will_quit)
    EGG_SM_CLIENT_GET_CLASS (client)->will_quit (client, will_quit);
}

/* Signal-emitting callbacks from platform-specific code */

GKeyFile *
egg_sm_client_save_state (EggSMClient *client)
{
  GKeyFile *state_file;
  char *group;

  state_file = g_key_file_new ();

  g_debug ("Emitting save_state");
  g_signal_emit (client, signals[SAVE_STATE], 0, state_file);
  g_debug ("Done emitting save_state");

  group = g_key_file_get_start_group (state_file);
  if (group)
    {
      g_free (group);
      return state_file;
    }
  else
    {
      g_key_file_free (state_file);
      return NULL;
    }
}

void
egg_sm_client_quit_requested (EggSMClient *client)
{
  if (!g_signal_has_handler_pending (client, signals[QUIT_REQUESTED], 0, FALSE))
    {
      g_debug ("Not emitting quit_requested because no one is listening");
      egg_sm_client_will_quit (client, TRUE);
      return;
    }

  g_debug ("Emitting quit_requested");
  g_signal_emit (client, signals[QUIT_REQUESTED], 0);
  g_debug ("Done emitting quit_requested");
}

void
egg_sm_client_quit_cancelled (EggSMClient *client)
{
  g_debug ("Emitting quit_cancelled");
  g_signal_emit (client, signals[QUIT_CANCELLED], 0);
  g_debug ("Done emitting quit_cancelled");
}

void
egg_sm_client_quit (EggSMClient *client)
{
  g_debug ("Emitting quit");
  g_signal_emit (client, signals[QUIT], 0);
  g_debug ("Done emitting quit");

  /* FIXME: should we just call gtk_main_quit() here? */
}

void
egg_sm_client_startup (EggSMClient *client)
{
  if (EGG_SM_CLIENT_GET_CLASS (client)->startup)
    EGG_SM_CLIENT_GET_CLASS (client)->startup (client, sm_client_id);
}

static void
egg_sm_client_debug_handler (const char *log_domain,
			     GLogLevelFlags log_level,
			     const char *message,
			     gpointer user_data)
{
  static int debug = -1;

  if (debug < 0)
    debug = (g_getenv ("EGG_SM_CLIENT_DEBUG") != NULL);

  if (debug)
    g_log_default_handler (log_domain, log_level, message, NULL);
}
