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

#include "sugar-clipboard.h"

/**
 * sugar_clipboard_set_with_data:
 * @clipboard: a #GtkClipboard
 * @targets: (array length=n_targets): array containing information
 *     about the available forms for the clipboard data
 * @n_targets: number of elements in @targets
 * @get_func: (closure user_data) (scope notified): function to call to get the
 *     actual clipboard data
 * @clear_func: (closure user_data) (scope async): when the clipboard
 *     contents are set again, this function will be called, and @get_func
 *     will not be subsequently called.
 * @user_data: user data to pass to @get_func and @clear_func.
 *
 * Virtually sets the contents of the specified clipboard by providing
 * a list of supported formats for the clipboard data and a function
 * to call to get the actual data when it is requested.
 *
 * Return value: %TRUE if setting the clipboard data succeeded.
 *    If setting the clipboard data failed the provided callback
 *    functions will be ignored.
 **/
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
