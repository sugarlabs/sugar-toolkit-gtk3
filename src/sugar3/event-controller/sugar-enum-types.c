
/* Generated data (by glib-mkenums) */

#include "sugar-event-controllers.h"

/* enumerations from "sugar-event-controller.h" */
GType
sugar_event_controller_state_get_type (void)
{
    static GType etype = 0;
    if (G_UNLIKELY(etype == 0)) {
        static const GEnumValue values[] = {
            { SUGAR_EVENT_CONTROLLER_STATE_NONE, "SUGAR_EVENT_CONTROLLER_STATE_NONE", "none" },
            { SUGAR_EVENT_CONTROLLER_STATE_COLLECTING, "SUGAR_EVENT_CONTROLLER_STATE_COLLECTING", "collecting" },
            { SUGAR_EVENT_CONTROLLER_STATE_RECOGNIZED, "SUGAR_EVENT_CONTROLLER_STATE_RECOGNIZED", "recognized" },
            { SUGAR_EVENT_CONTROLLER_STATE_NOT_RECOGNIZED, "SUGAR_EVENT_CONTROLLER_STATE_NOT_RECOGNIZED", "not-recognized" },
            { 0, NULL, NULL }
        };
        etype = g_enum_register_static (g_intern_static_string ("SugarEventControllerState"), values);
    }
    return etype;
}

GType
sugar_event_controller_flags_get_type (void)
{
    static GType etype = 0;
    if (G_UNLIKELY(etype == 0)) {
        static const GFlagsValue values[] = {
            { SUGAR_EVENT_CONTROLLER_FLAG_NONE, "SUGAR_EVENT_CONTROLLER_FLAG_NONE", "none" },
            { SUGAR_EVENT_CONTROLLER_FLAG_EXCLUSIVE, "SUGAR_EVENT_CONTROLLER_FLAG_EXCLUSIVE", "exclusive" },
            { 0, NULL, NULL }
        };
        etype = g_flags_register_static (g_intern_static_string ("SugarEventControllerFlags"), values);
    }
    return etype;
}

/* enumerations from "sugar-swipe-controller.h" */
GType
sugar_swipe_direction_get_type (void)
{
    static GType etype = 0;
    if (G_UNLIKELY(etype == 0)) {
        static const GEnumValue values[] = {
            { SUGAR_SWIPE_DIRECTION_LEFT, "SUGAR_SWIPE_DIRECTION_LEFT", "left" },
            { SUGAR_SWIPE_DIRECTION_RIGHT, "SUGAR_SWIPE_DIRECTION_RIGHT", "right" },
            { SUGAR_SWIPE_DIRECTION_UP, "SUGAR_SWIPE_DIRECTION_UP", "up" },
            { SUGAR_SWIPE_DIRECTION_DOWN, "SUGAR_SWIPE_DIRECTION_DOWN", "down" },
            { 0, NULL, NULL }
        };
        etype = g_enum_register_static (g_intern_static_string ("SugarSwipeDirection"), values);
    }
    return etype;
}

GType
sugar_swipe_direction_flags_get_type (void)
{
    static GType etype = 0;
    if (G_UNLIKELY(etype == 0)) {
        static const GFlagsValue values[] = {
            { SUGAR_SWIPE_DIRECTION_FLAG_LEFT, "SUGAR_SWIPE_DIRECTION_FLAG_LEFT", "left" },
            { SUGAR_SWIPE_DIRECTION_FLAG_RIGHT, "SUGAR_SWIPE_DIRECTION_FLAG_RIGHT", "right" },
            { SUGAR_SWIPE_DIRECTION_FLAG_UP, "SUGAR_SWIPE_DIRECTION_FLAG_UP", "up" },
            { SUGAR_SWIPE_DIRECTION_FLAG_DOWN, "SUGAR_SWIPE_DIRECTION_FLAG_DOWN", "down" },
            { 0, NULL, NULL }
        };
        etype = g_flags_register_static (g_intern_static_string ("SugarSwipeDirectionFlags"), values);
    }
    return etype;
}



/* Generated data ends here */

