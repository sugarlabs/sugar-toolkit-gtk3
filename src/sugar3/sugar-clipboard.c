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

#include <gtk/gtk.h>
#include "sugar-clipboard.h"

/**
 * sugar_clipboard_set_with_data:
 * @clipboard: a clipboard object. In GTK3, this is a #GtkClipboard. In GTK4, it is a #GdkClipboard.
 * @targets: (array length=n_targets): array containing information about the available clipboard formats.
 * @n_targets: number of elements in @targets.
 * @get_func: a callback to retrieve the clipboard data.
 * @clear_func: a callback to clear the clipboard data when it is updated.
 * @user_data: user data to pass to @get_func and @clear_func.
 *
 * Sets the contents of the specified clipboard by providing a list of supported
 * formats and callbacks to retrieve or clear the data.
 *
 * Return value: %TRUE if setting the clipboard data succeeded.
 */
#if GTK_CHECK_VERSION(4, 0, 0)
gboolean
sugar_clipboard_set_with_data (GdkClipboard *clipboard,
                               const GtkTargetEntry *targets,
                               guint n_targets,
                               GtkClipboardGetFunc get_func,
                               GtkClipboardClearFunc clear_func,
                               gpointer user_data)
{
    /* 
     * In GTK4 the clipboard API has changed.
     * Replace this stub with an implementation using the new GTK4 clipboard API,
     * such as using gdk_clipboard_set_content() with a GdkContentProvider.
     */
    g_warning ("sugar_clipboard_set_with_data is not yet implemented for GTK4.");
    return FALSE;
}
#else
gboolean
sugar_clipboard_set_with_data (GtkClipboard *clipboard,
                               const GtkTargetEntry *targets,
                               guint n_targets,
                               GtkClipboardGetFunc get_func,
                               GtkClipboardClearFunc clear_func,
                               gpointer user_data)
{
    return gtk_clipboard_set_with_data (clipboard,
                                        targets,
                                        n_targets,
                                        get_func,
                                        clear_func,
                                        user_data);
}
#endif
