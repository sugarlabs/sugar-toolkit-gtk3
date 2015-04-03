/*
 * Copyright (C) 2014, Martin Abente Lahaye - tch@sugarlabs.org
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
 */

#ifndef __SUGAR_CLIPBOARD_H__
#define __SUGAR_CLIPBOARD_H__

#include <gtk/gtk.h>

G_BEGIN_DECLS

gboolean
sugar_clipboard_set_with_data (GtkClipboard *clipboard,
                               const GtkTargetEntry *targets,
                               guint n_targets,
                               GtkClipboardGetFunc get_func,
                               GtkClipboardClearFunc clear_func,
                               gpointer user_data);

G_END_DECLS

#endif /* __SUGAR_CLIPBOARD_H__ */

