/* client-xsmp.c
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

#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include "gsm-client-xsmp.h"
#include "gsm-session.h"

/* FIXME */
#define GsmDesktopFile "_Gsm_DesktopFile"

static gboolean client_iochannel_watch  (GIOChannel   *channel,
					 GIOCondition  condition,
					 gpointer      data);
static gboolean client_protocol_timeout (gpointer      data);

static void set_description (GsmClientXSMP *xsmp);

static const char *xsmp_get_client_id       (GsmClient *client);
static pid_t       xsmp_get_pid             (GsmClient *client);
static char       *xsmp_get_desktop_file    (GsmClient *client);
static char       *xsmp_get_restart_command (GsmClient *client);
static char       *xsmp_get_discard_command (GsmClient *client);
static gboolean    xsmp_get_autorestart     (GsmClient *client);

static void xsmp_finalize             (GObject   *object);
static void xsmp_restart              (GsmClient *client,
                                       GError   **error);
static void xsmp_save_yourself        (GsmClient *client,
				       gboolean   save_state);
static void xsmp_save_yourself_phase2 (GsmClient *client);
static void xsmp_interact             (GsmClient *client);
static void xsmp_shutdown_cancelled   (GsmClient *client);
static void xsmp_die                  (GsmClient *client);

G_DEFINE_TYPE (GsmClientXSMP, gsm_client_xsmp, GSM_TYPE_CLIENT)

static void
gsm_client_xsmp_init (GsmClientXSMP *xsmp)
{
  ;
}

static void
gsm_client_xsmp_class_init (GsmClientXSMPClass *klass)
{
  GObjectClass *object_class = G_OBJECT_CLASS (klass);
  GsmClientClass *client_class = GSM_CLIENT_CLASS (klass);

  object_class->finalize             = xsmp_finalize;

  client_class->get_client_id        = xsmp_get_client_id;
  client_class->get_pid              = xsmp_get_pid;
  client_class->get_desktop_file     = xsmp_get_desktop_file;
  client_class->get_restart_command  = xsmp_get_restart_command;
  client_class->get_discard_command  = xsmp_get_discard_command;
  client_class->get_autorestart      = xsmp_get_autorestart;

  client_class->restart              = xsmp_restart;
  client_class->save_yourself        = xsmp_save_yourself;
  client_class->save_yourself_phase2 = xsmp_save_yourself_phase2;
  client_class->interact             = xsmp_interact;
  client_class->shutdown_cancelled   = xsmp_shutdown_cancelled;
  client_class->die                  = xsmp_die;
}

GsmClientXSMP *
gsm_client_xsmp_new (IceConn ice_conn)
{
  GsmClientXSMP *xsmp;
  GIOChannel *channel;
  int fd;

  xsmp = g_object_new (GSM_TYPE_CLIENT_XSMP, NULL);
  xsmp->props = g_ptr_array_new ();

  xsmp->ice_conn = ice_conn;
  xsmp->current_save_yourself = -1;
  xsmp->next_save_yourself = -1;

  fd = IceConnectionNumber (ice_conn);
  fcntl (fd, F_SETFD, fcntl (fd, F_GETFD, 0) | FD_CLOEXEC);

  channel = g_io_channel_unix_new (fd);
  xsmp->watch_id = g_io_add_watch (channel, G_IO_IN | G_IO_ERR,
				   client_iochannel_watch, xsmp);
  g_io_channel_unref (channel);

  xsmp->protocol_timeout = g_timeout_add_seconds (5, client_protocol_timeout, xsmp);

  set_description (xsmp);
  g_debug ("New client '%s'", xsmp->description);

  return xsmp;
}

static void
xsmp_finalize (GObject *object)
{
  GsmClientXSMP *xsmp = (GsmClientXSMP *) object;

  g_debug ("xsmp_finalize (%s)", xsmp->description);

  if (xsmp->watch_id)
    g_source_remove (xsmp->watch_id);

  if (xsmp->conn)
    SmsCleanUp (xsmp->conn);
  else
    IceCloseConnection (xsmp->ice_conn);

  if (xsmp->protocol_timeout)
    g_source_remove (xsmp->protocol_timeout);

  G_OBJECT_CLASS (gsm_client_xsmp_parent_class)->finalize (object);
}

static gboolean
client_iochannel_watch (GIOChannel   *channel,
			GIOCondition  condition,
			gpointer      data)
{
  GsmClient *client = data;
  GsmClientXSMP *xsmp = data;

  switch (IceProcessMessages (xsmp->ice_conn, NULL, NULL))
    {
    case IceProcessMessagesSuccess:
      return TRUE;

    case IceProcessMessagesIOError:
      g_debug ("IceProcessMessagesIOError on '%s'", xsmp->description);
      gsm_client_disconnected (client);
      return FALSE;

    case IceProcessMessagesConnectionClosed:
      g_debug ("IceProcessMessagesConnectionClosed on '%s'",
	       xsmp->description);
      return FALSE;

    default:
      g_assert_not_reached ();
    }
}

/* Called if too much time passes between the initial connection and
 * the XSMP protocol setup.
 */
static gboolean
client_protocol_timeout (gpointer data)
{
  GsmClient *client = data;
  GsmClientXSMP *xsmp = data;

  g_debug ("client_protocol_timeout for client '%s' in ICE status %d",
	   xsmp->description, IceConnectionStatus (xsmp->ice_conn));
  gsm_client_disconnected (client);

  return FALSE;
}

static Status
register_client_callback (SmsConn    conn,
			  SmPointer  manager_data,
			  char      *previous_id)
{
  GsmClient *client = manager_data;
  GsmClientXSMP *xsmp = manager_data;
  char *id;

  g_debug ("Client '%s' received RegisterClient(%s)",
           xsmp->description,
	   previous_id ? previous_id : "NULL");

  id = gsm_session_register_client (global_session, client, previous_id);

  if (id == NULL)
    {
      g_debug ("  rejected: invalid previous_id");
      free (previous_id);
      return FALSE;
    }

  xsmp->id = id;

  set_description (xsmp);

  g_debug ("Sending RegisterClientReply to '%s'", xsmp->description);

  SmsRegisterClientReply (conn, xsmp->id);

  if (!previous_id)
    {
      /* Send the initial SaveYourself. */
      g_debug ("Sending initial SaveYourself");
      SmsSaveYourself (conn, SmSaveLocal, False, SmInteractStyleNone, False);
      xsmp->current_save_yourself = SmSaveLocal;

      free (previous_id);
    }

  return TRUE;
}

static void
do_save_yourself (GsmClientXSMP *xsmp, int save_type)
{
  if (xsmp->next_save_yourself != -1)
    {
      /* Either we're currently doing a shutdown and there's a checkpoint
       * queued after it, or vice versa. Either way, the new SaveYourself
       * is redundant.
       */
      g_debug ("  skipping redundant SaveYourself for '%s'",
	       xsmp->description);
    }
  else if (xsmp->current_save_yourself != -1)
    {
      g_debug ("  queuing new SaveYourself for '%s'",
	       xsmp->description);
      xsmp->next_save_yourself = save_type;
    }
  else
    {
      xsmp->current_save_yourself = save_type;

      switch (save_type)
	{
	case SmSaveLocal:
	  /* Save state */
	  SmsSaveYourself (xsmp->conn, SmSaveLocal, FALSE,
			   SmInteractStyleNone, FALSE);
	  break;

	default:
	  /* Logout */
	  SmsSaveYourself (xsmp->conn, save_type, TRUE,
			   SmInteractStyleAny, FALSE);
	  break;
	}
    }
}

static void
save_yourself_request_callback (SmsConn   conn,
                                SmPointer manager_data,
                                int       save_type,
                                Bool      shutdown,
                                int       interact_style,
                                Bool      fast,
                                Bool      global)
{
  GsmClientXSMP *xsmp = manager_data;

  g_debug ("Client '%s' received SaveYourselfRequest(%s, %s, %s, %s, %s)",
	   xsmp->description,
	   save_type == SmSaveLocal ? "SmSaveLocal" :
	   save_type == SmSaveGlobal ? "SmSaveGlobal" : "SmSaveBoth",
	   shutdown ? "Shutdown" : "!Shutdown",
	   interact_style == SmInteractStyleAny ? "SmInteractStyleAny" :
	   interact_style == SmInteractStyleErrors ? "SmInteractStyleErrors" :
	   "SmInteractStyleNone", fast ? "Fast" : "!Fast",
	   global ? "Global" : "!Global");

  /* Examining the g_debug above, you can see that there are a total
   * of 72 different combinations of options that this could have been
   * called with. However, most of them are stupid.
   *
   * If @shutdown and @global are both TRUE, that means the caller is
   * requesting that a logout message be sent to all clients, so we do
   * that. We use @fast to decide whether or not to show a
   * confirmation dialog. (This isn't really what @fast is for, but
   * the old gnome-session and ksmserver both interpret it that way,
   * so we do too.) We ignore @save_type because we pick the correct
   * save_type ourselves later based on user prefs, dialog choices,
   * etc, and we ignore @interact_style, because clients have not used
   * it correctly consistently enough to make it worth honoring.
   *
   * If @shutdown is TRUE and @global is FALSE, the caller is
   * confused, so we ignore the request.
   *
   * If @shutdown is FALSE and @save_type is SmSaveGlobal or
   * SmSaveBoth, then the client wants us to ask some or all open
   * applications to save open files to disk, but NOT quit. This is
   * silly and so we ignore the request.
   *
   * If @shutdown is FALSE and @save_type is SmSaveLocal, then the
   * client wants us to ask some or all open applications to update
   * their current saved state, but not log out. At the moment, the
   * code only supports this for the !global case (ie, a client
   * requesting that it be allowed to update *its own* saved state,
   * but not having everyone else update their saved state).
   */

  if (shutdown && global)
    {
      g_debug ("  initiating shutdown");
/*      gsm_session_initiate_shutdown (global_session,
                                     !fast,
                                     GSM_SESSION_LOGOUT_TYPE_LOGOUT);
*/
    }
  else if (!shutdown && !global)
    {
      g_debug ("  initiating checkpoint");
      do_save_yourself (xsmp, SmSaveLocal);
    }
  else
    g_debug ("  ignoring");
}

static void
xsmp_restart (GsmClient *client, GError **error)
{
  char *restart_cmd = gsm_client_get_restart_command (client);

  g_spawn_command_line_async (restart_cmd, error);

  g_free (restart_cmd);
}

static void
xsmp_save_yourself (GsmClient *client, gboolean save_state)
{
  GsmClientXSMP *xsmp = (GsmClientXSMP *)client;

  g_debug ("xsmp_save_yourself ('%s', %s)", xsmp->description,
	   save_state ? "True" : "False");

  do_save_yourself (xsmp, save_state ? SmSaveBoth : SmSaveGlobal);
}

static void
save_yourself_phase2_request_callback (SmsConn   conn,
                                       SmPointer manager_data)
{
  GsmClient *client = manager_data;
  GsmClientXSMP *xsmp = manager_data;

  g_debug ("Client '%s' received SaveYourselfPhase2Request",
	   xsmp->description);

  if (xsmp->current_save_yourself == SmSaveLocal)
    {
      /* WTF? Anyway, if it's checkpointing, it doesn't have to wait
       * for anyone else.
       */
      SmsSaveYourselfPhase2 (xsmp->conn);
    }
  else
    gsm_client_request_phase2 (client);
}

static void
xsmp_save_yourself_phase2 (GsmClient *client)
{
  GsmClientXSMP *xsmp = (GsmClientXSMP *)client;

  g_debug ("xsmp_save_yourself_phase2 ('%s')", xsmp->description);

  SmsSaveYourselfPhase2 (xsmp->conn);
}

static void
interact_request_callback (SmsConn   conn,
                           SmPointer manager_data,
                           int       dialog_type)
{
  GsmClient *client = manager_data;
  GsmClientXSMP *xsmp = manager_data;

  g_debug ("Client '%s' received InteractRequest(%s)", xsmp->description,
	   dialog_type == SmInteractStyleAny ? "Any" : "Errors");

  gsm_client_request_interaction (client);
}

static void
xsmp_interact (GsmClient *client)
{
  GsmClientXSMP *xsmp = (GsmClientXSMP *) client;

  g_debug ("xsmp_interact ('%s')", xsmp->description);

  SmsInteract (xsmp->conn);
}

static void
interact_done_callback (SmsConn   conn,
                        SmPointer manager_data,
                        Bool      cancel_shutdown)
{
  GsmClient *client = manager_data;
  GsmClientXSMP *xsmp = manager_data;

  g_debug ("Client '%s' received InteractDone(cancel_shutdown = %s)",
	   xsmp->description, cancel_shutdown ? "True" : "False");

  gsm_client_interaction_done (client, cancel_shutdown);
}

static void
xsmp_shutdown_cancelled (GsmClient *client)
{
  GsmClientXSMP *xsmp = (GsmClientXSMP *) client;

  g_debug ("xsmp_shutdown_cancelled ('%s')", xsmp->description);

  SmsShutdownCancelled (xsmp->conn);
}

static void
xsmp_die (GsmClient *client)
{
  GsmClientXSMP *xsmp = (GsmClientXSMP *) client;

  g_debug ("xsmp_die ('%s')", xsmp->description);

  SmsDie (xsmp->conn);
}

static void
save_yourself_done_callback (SmsConn   conn,
			     SmPointer manager_data,
			     Bool      success)
{
  GsmClient *client = manager_data;
  GsmClientXSMP *xsmp = manager_data;

  g_debug ("Client '%s' received SaveYourselfDone(success = %s)",
	   xsmp->description, success ? "True" : "False");

  if (xsmp->current_save_yourself == SmSaveLocal)
    {
      xsmp->current_save_yourself = -1;
      SmsSaveComplete (xsmp->conn);
      gsm_client_saved_state (client);
    }
  else
    {
      xsmp->current_save_yourself = -1;
      gsm_client_save_yourself_done (client);
    }

  if (xsmp->next_save_yourself)
    {
      int save_type = xsmp->next_save_yourself;

      xsmp->next_save_yourself = -1;
      do_save_yourself (xsmp, save_type);
    }
}

static void
close_connection_callback (SmsConn     conn,
			   SmPointer   manager_data,
			   int         count,
			   char      **reason_msgs)
{
  GsmClient *client = manager_data;
  GsmClientXSMP *xsmp = manager_data;
  int i;

  g_debug ("Client '%s' received CloseConnection", xsmp->description);
  for (i = 0; i < count; i++)
    g_debug (" close reason: '%s'", reason_msgs[i]);
  SmFreeReasons (count, reason_msgs);

  gsm_client_disconnected (client);
}

static void
debug_print_property (SmProp *prop)
{
  GString *tmp;
  int i;

  switch (prop->type[0])
    {
    case 'C': /* CARD8 */
      g_debug ("  %s = %d", prop->name, *(unsigned char *)prop->vals[0].value);
      break;

    case 'A': /* ARRAY8 */
      g_debug ("  %s = '%s'", prop->name, (char *)prop->vals[0].value);
      break;

    case 'L': /* LISTofARRAY8 */
      tmp = g_string_new (NULL);
      for (i = 0; i < prop->num_vals; i++)
	{
	  g_string_append_printf (tmp, "'%.*s' ", prop->vals[i].length,
				  (char *)prop->vals[i].value);
	}
      g_debug ("  %s = %s", prop->name, tmp->str);
      g_string_free (tmp, TRUE);
      break;

    default:
      g_debug ("  %s = ??? (%s)", prop->name, prop->type);
      break;
    }
}

static SmProp *
find_property (GsmClientXSMP *client, const char *name, int *index)
{
  SmProp *prop;
  int i;

  for (i = 0; i < client->props->len; i++)
    {
      prop = client->props->pdata[i];

      if (!strcmp (prop->name, name))
	{
	  if (index)
	    *index = i;
	  return prop;
	}
    }

  return NULL;
}

static void
delete_property (GsmClientXSMP *client, const char *name)
{
  int index;
  SmProp *prop;

  prop = find_property (client, name, &index);
  if (!prop)
    return;

#if 0
  /* This is wrong anyway; we can't unconditionally run the current
   * discard command; if this client corresponds to a GsmAppResumed,
   * and the current discard command is identical to the app's
   * discard_command, then we don't run the discard command now,
   * because that would delete a saved state we may want to resume
   * again later.
   */
  if (!strcmp (name, SmDiscardCommand))
    gsm_client_run_discard (client);
#endif

  g_ptr_array_remove_index_fast (client->props, index);
  SmFreeProperty (prop);
}

static void
set_properties_callback (SmsConn     conn,
                         SmPointer   manager_data,
                         int         num_props,
                         SmProp    **props)
{
  GsmClientXSMP *client = manager_data;
  int i;

  g_debug ("Set properties from client '%s'", client->description);

  for (i = 0; i < num_props; i++)
    {
      delete_property (client, props[i]->name);
      g_ptr_array_add (client->props, props[i]);

      debug_print_property (props[i]);

      if (!strcmp (props[i]->name, SmProgram))
	set_description (client);
    }

  free (props);

}

static void
delete_properties_callback (SmsConn     conn,
                            SmPointer   manager_data,
                            int         num_props,
                            char      **prop_names)
{
  GsmClientXSMP *client = manager_data;
  int i;

  g_debug ("Delete properties from '%s'", client->description);

  for (i = 0; i < num_props; i++)
    {
      delete_property (client, prop_names[i]);

      g_debug ("  %s", prop_names[i]);
    }

  free (prop_names);
}

static void
get_properties_callback (SmsConn   conn,
                         SmPointer manager_data)
{
  GsmClientXSMP *client = manager_data;

  g_debug ("Get properties request from '%s'", client->description);

  SmsReturnProperties (conn, client->props->len,
		       (SmProp **)client->props->pdata);
}

static const char *
xsmp_get_client_id (GsmClient *client)
{
  GsmClientXSMP *xsmp = (GsmClientXSMP *) client;

  return xsmp->id;
}

static pid_t
xsmp_get_pid (GsmClient *client)
{
  GsmClientXSMP *xsmp = (GsmClientXSMP *) client;
  SmProp *prop = find_property (xsmp, SmProcessID, NULL);
  char buf[32];

  if (!prop || strcmp (prop->type, SmARRAY8) != 0)
    return (pid_t)-1;

  /* prop->vals[0].value might not be '\0'-terminated... */
  g_strlcpy (buf, prop->vals[0].value, MIN (prop->vals[0].length, sizeof (buf)));
  return (pid_t)strtoul (buf, NULL, 10);
}

static char *
xsmp_get_desktop_file (GsmClient *client)
{
  GsmClientXSMP *xsmp = (GsmClientXSMP *) client;
  SmProp *prop = find_property (xsmp, GsmDesktopFile, NULL);

  if (!prop || strcmp (prop->type, SmARRAY8) != 0)
    return NULL;

  return g_strndup (prop->vals[0].value, prop->vals[0].length);
}

static char *
prop_to_command (SmProp *prop)
{
  GString *str;
  int i, j;
  gboolean need_quotes;

  str = g_string_new (NULL);
  for (i = 0; i < prop->num_vals; i++)
    {
      char *val = prop->vals[i].value;

      need_quotes = FALSE;
      for (j = 0; j < prop->vals[i].length; j++)
	{
	  if (!g_ascii_isalnum (val[j]) && !strchr ("-_=:./", val[j]))
	    {
	      need_quotes = TRUE;
	      break;
	    }
	}

      if (i > 0)
	g_string_append_c (str, ' ');

      if (!need_quotes)
	{
	  g_string_append_printf (str, "%.*s", prop->vals[i].length,
				  (char *)prop->vals[i].value);
	}
      else
	{
	  g_string_append_c (str, '\'');
	  while (val < (char *)prop->vals[i].value + prop->vals[i].length)
	    {
	      if (*val == '\'')
		g_string_append (str, "'\''");
	      else
		g_string_append_c (str, *val);
	      val++;
	    }
	  g_string_append_c (str, '\'');
	}
    }

  return g_string_free (str, FALSE);
}

static char *
xsmp_get_restart_command (GsmClient *client)
{
  GsmClientXSMP *xsmp = (GsmClientXSMP *) client;
  SmProp *prop = find_property (xsmp, SmRestartCommand, NULL);

  if (!prop || strcmp (prop->type, SmLISTofARRAY8) != 0)
    return NULL;

  return prop_to_command (prop);
}

static char *
xsmp_get_discard_command (GsmClient *client)
{
  GsmClientXSMP *xsmp = (GsmClientXSMP *) client;
  SmProp *prop = find_property (xsmp, SmDiscardCommand, NULL);

  if (!prop || strcmp (prop->type, SmLISTofARRAY8) != 0)
    return NULL;

  return prop_to_command (prop);
}

static gboolean
xsmp_get_autorestart (GsmClient *client)
{
  GsmClientXSMP *xsmp = (GsmClientXSMP *) client;
  SmProp *prop = find_property (xsmp, SmRestartStyleHint, NULL);

  if (!prop || strcmp (prop->type, SmCARD8) != 0)
    return FALSE;

  return ((unsigned char *)prop->vals[0].value)[0] == SmRestartImmediately;
}

static void
set_description (GsmClientXSMP *client)
{
  SmProp *prop = find_property (client, SmProgram, NULL);

  g_free (client->description);
  if (prop)
    {
      client->description = g_strdup_printf ("%p [%.*s %s]", client,
					     prop->vals[0].length,
					     (char *)prop->vals[0].value,
					     client->id);
    }
  else if (client->id)
    client->description = g_strdup_printf ("%p [%s]", client, client->id);
  else
    client->description = g_strdup_printf ("%p", client);
}

void
gsm_client_xsmp_connect (GsmClientXSMP *client, SmsConn conn,
			 unsigned long *mask_ret, SmsCallbacks *callbacks_ret)
{
  client->conn = conn;

  if (client->protocol_timeout)
    {
      g_source_remove (client->protocol_timeout);
      client->protocol_timeout = 0;
    }

  g_debug ("Initializing client %s", client->description);

  *mask_ret = 0;

  *mask_ret |= SmsRegisterClientProcMask;
  callbacks_ret->register_client.callback = register_client_callback;
  callbacks_ret->register_client.manager_data  = client;

  *mask_ret |= SmsInteractRequestProcMask;
  callbacks_ret->interact_request.callback = interact_request_callback;
  callbacks_ret->interact_request.manager_data = client;

  *mask_ret |= SmsInteractDoneProcMask;
  callbacks_ret->interact_done.callback = interact_done_callback;
  callbacks_ret->interact_done.manager_data = client;

  *mask_ret |= SmsSaveYourselfRequestProcMask;
  callbacks_ret->save_yourself_request.callback = save_yourself_request_callback;
  callbacks_ret->save_yourself_request.manager_data = client;

  *mask_ret |= SmsSaveYourselfP2RequestProcMask;
  callbacks_ret->save_yourself_phase2_request.callback = save_yourself_phase2_request_callback;
  callbacks_ret->save_yourself_phase2_request.manager_data = client;

  *mask_ret |= SmsSaveYourselfDoneProcMask;
  callbacks_ret->save_yourself_done.callback = save_yourself_done_callback;
  callbacks_ret->save_yourself_done.manager_data = client;

  *mask_ret |= SmsCloseConnectionProcMask;
  callbacks_ret->close_connection.callback = close_connection_callback;
  callbacks_ret->close_connection.manager_data  = client;

  *mask_ret |= SmsSetPropertiesProcMask;
  callbacks_ret->set_properties.callback = set_properties_callback;
  callbacks_ret->set_properties.manager_data = client;

  *mask_ret |= SmsDeletePropertiesProcMask;
  callbacks_ret->delete_properties.callback = delete_properties_callback;
  callbacks_ret->delete_properties.manager_data = client;

  *mask_ret |= SmsGetPropertiesProcMask;
  callbacks_ret->get_properties.callback = get_properties_callback;
  callbacks_ret->get_properties.manager_data = client;
}
