/*
 * Copyright (C) 2008, Red Hat, Inc.
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

#ifndef __SUGAR_GRID_H__
#define __SUGAR_GRID_H__

#include <glib-object.h>
#include <gdk/gdk.h>

G_BEGIN_DECLS

typedef struct _SugarGrid SugarGrid;
typedef struct _SugarGridClass SugarGridClass;

#define SUGAR_TYPE_GRID			     (sugar_grid_get_type())
#define SUGAR_GRID(object)	         (G_TYPE_CHECK_INSTANCE_CAST((object), SUGAR_TYPE_GRID, SugarGrid))
#define SUGAR_GRID_CLASS(klass)	     (G_TYPE_CHACK_CLASS_CAST((klass), SUGAR_TYPE_GRID, SugarGridClass))
#define SUGAR_IS_GRID(object)	     (G_TYPE_CHECK_INSTANCE_TYPE((object), SUGAR_TYPE_GRID))
#define SUGAR_IS_GRID_CLASS(klass)   (G_TYPE_CHECK_CLASS_TYPE((klass), SUGAR_TYPE_GRID))
#define SUGAR_GRID_GET_CLASS(object) (G_TYPE_INSTANCE_GET_CLASS((object), SUGAR_TYPE_GRID, SugarGridClass))

struct _SugarGrid {
    GObject base_instance;

    gint width;
    gint height;
    guchar *weights;
};

struct _SugarGridClass {
	GObjectClass base_class;
};

GType	 sugar_grid_get_type       (void);
void     sugar_grid_setup          (SugarGrid    *grid,
                                    gint          width,
                                    gint          height);
void     sugar_grid_add_weight     (SugarGrid    *grid,
                                    GdkRectangle *rect);
void     sugar_grid_remove_weight  (SugarGrid    *grid,
                                    GdkRectangle *rect);
guint    sugar_grid_compute_weight (SugarGrid    *grid,
                                    GdkRectangle *rect);

G_END_DECLS

#endif /* __SUGAR_GRID_H__ */
