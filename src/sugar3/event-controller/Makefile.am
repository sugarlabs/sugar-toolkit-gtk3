lib_LTLIBRARIES = libsugar-eventcontroller.la

libsugar_eventcontroller_la_LDFLAGS = $(LDADD)
libsugar_eventcontroller_la_LIBADD = $(EXT_LIBS)

libsugar_eventcontrollerincludedir = $(includedir)/sugar-3.0/event-controller/

libsugar_eventcontroller_la_CFLAGS = 	\
	$(EXT_CFLAGS)			\
	$(WARN_FLAGS)			\
	-DSUGAR_TOOLKIT_COMPILATION

eventcontroller_h_sources = 		\
	sugar-event-controller.h	\
	sugar-event-controllers.h	\
	sugar-long-press-controller.h	\
	sugar-rotate-controller.h	\
	sugar-swipe-controller.h	\
	sugar-touch-controller.h	\
	sugar-zoom-controller.h

eventcontroller_c_sources =		\
	sugar-event-controller.c	\
	sugar-long-press-controller.c	\
	sugar-rotate-controller.c	\
	sugar-swipe-controller.c	\
	sugar-touch-controller.c	\
	sugar-zoom-controller.c


libsugar_eventcontroller_la_SOURCES =	\
	$(BUILT_SOURCES)		\
	$(eventcontroller_h_sources)	\
	$(eventcontroller_c_sources)

BUILT_SOURCES = 			\
	sugar-enum-types.c		\
	sugar-enum-types.h

sugar-enum-types.h: sugar-enum-types.h.template $(eventcontroller_h_sources)
	$(AM_V_GEN) (cd $(srcdir) && $(GLIB_MKENUMS) --template sugar-enum-types.h.template $(eventcontroller_h_sources)) > $@

sugar-enum-types.c: sugar-enum-types.c.template $(eventcontroller_h_sources)
	$(AM_V_GEN) (cd $(srcdir) && $(GLIB_MKENUMS) --template sugar-enum-types.c.template $(eventcontroller_h_sources)) > $@

EXTRA_DIST =				\
	sugar-enum-types.c.template	\
	sugar-enum-types.h.template

-include $(INTROSPECTION_MAKEFILE)
INTROSPECTION_GIRS = SugarGestures-1.0.gir
INTROSPECTION_SCANNER_ARGS = --identifier-prefix=Sugar --symbol-prefix=sugar
SugarGestures_1_0_gir_LIBS = libsugar-eventcontroller.la
SugarGestures_1_0_gir_FILES =	\
	$(BUILT_SOURCES)		\
	$(eventcontroller_h_sources)	\
	$(eventcontroller_c_sources)
SugarGestures_1_0_gir_CFLAGS =	\
	-DSUGAR_TOOLKIT_COMPILATION --warn-all

SugarGestures-1.0.gir: libsugar-eventcontroller.la
SugarGestures_1_0_gir_INCLUDES = Gtk-3.0 Gdk-3.0
SugarGestures_1_0_gir_PACKAGES = gtk+-3.0 gdk-3.0
SugarGestures_1_0_gir_EXPORT_PACKAGES = SugarGestures-1.0

girdir = $(datadir)/gir-1.0
gir_DATA = $(INTROSPECTION_GIRS)

typelibdir = $(libdir)/girepository-1.0
typelib_DATA = $(INTROSPECTION_GIRS:.gir=.typelib)

CLEANFILES = $(BUILT_SOURCES) $(gir_DATA) $(typelib_DATA)
