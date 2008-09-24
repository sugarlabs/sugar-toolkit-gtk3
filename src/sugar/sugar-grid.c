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

#include "sugar-grid.h"

static void sugar_grid_class_init (SugarGridClass *grid_class);
static void sugar_grid_init       (SugarGrid *grid);


G_DEFINE_TYPE(SugarGrid, sugar_grid, G_TYPE_OBJECT)

void
sugar_grid_setup(SugarGrid *grid, gint width, gint height)
{
    g_free(grid->weights);

    grid->weights = g_new0(guchar, width * height);
    grid->width = width;
    grid->height = height;
}

static gboolean
check_bounds(SugarGrid *grid, GdkRectangle *rect)
{
    return (grid->weights != NULL &&
            grid->width >= rect->x + rect->width &&
            grid->height >= rect->y + rect->height);
}

void
sugar_grid_add_weight(SugarGrid *grid, GdkRectangle *rect)
{
    int i, k;

    if (!check_bounds(grid, rect)) {
        g_warning("Trying to add weight outside the grid bounds.");
        return;
    }

    for (k = rect->y; k < rect->y + rect->height; k++) {
        for (i = rect->x; i < rect->x + rect->width; i++) {
            grid->weights[i + k * grid->width] += 1;
        }
    }
}

void
sugar_grid_remove_weight(SugarGrid *grid, GdkRectangle *rect)
{
    int i, k;

    if (!check_bounds(grid, rect)) {
        g_warning("Trying to remove weight outside the grid bounds.");
        return;
    }

    for (k = rect->y; k < rect->y + rect->height; k++) {
        for (i = rect->x; i < rect->x + rect->width; i++) {
            grid->weights[i + k * grid->width] -= 1;
        }
    }
}

guint
sugar_grid_compute_weight(SugarGrid *grid, GdkRectangle *rect)
{
    int i, k, sum = 0;

    if (!check_bounds(grid, rect)) {
        g_warning("Trying to compute weight outside the grid bounds.");
        return 0;
    }

    for (k = rect->y; k < rect->y + rect->height; k++) {
        for (i = rect->x; i < rect->x + rect->width; i++) {
            sum += grid->weights[i + k * grid->width];
        }
    }

    return sum;
}

static void
sugar_grid_finalize(GObject *object)
{
    SugarGrid *grid = SUGAR_GRID(object);

    g_free(grid->weights);
}

static void
sugar_grid_class_init(SugarGridClass *grid_class)
{
    GObjectClass *gobject_class;

    gobject_class = G_OBJECT_CLASS(grid_class);
    gobject_class->finalize = sugar_grid_finalize;
}

static void
sugar_grid_init(SugarGrid *grid)
{
    grid->weights = NULL;
}
