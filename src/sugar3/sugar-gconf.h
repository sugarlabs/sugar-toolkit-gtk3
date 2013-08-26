/*
 * Copyright (C) 2013, Daniel Narvaez
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

#ifndef __SUGAR_GCONF_H__
#define __SUGAR_GCONF_H__

#include <gconf/gconf-client.h>

G_BEGIN_DECLS

void sugar_gconf_client_set_string_list (GConfClient *client,
                                         const char *key,
                                         GSList *list,
                                         GError *err);

G_END_DECLS

#endif /* __SUGAR_GCONF_H__ */
