SUBDIRS = activity bundle event-controller graphics presence datastore dispatch

sugardir = $(pythondir)/sugar3
sugar_PYTHON =		\
	__init__.py	\
	env.py		\
	logger.py	\
	mime.py		\
        network.py	\
	profile.py	\
	session.py	\
	util.py

lib_LTLIBRARIES = libsugarext.la

libsugarext_la_CFLAGS = 		\
	-DHAVE_ALSA		\
	$(EXT_CFLAGS)	\
	$(WARN_CFLAGS)

libsugarext_la_LDFLAGS = $(LDADD)
libsugarext_la_LIBADD = $(EXT_LIBS) -lSM -lICE -lasound

libsugarext_la_SOURCES =		\
	$(BUILT_SOURCES)		\
	acme-volume-alsa.c		\
	acme-volume-alsa.h		\
	acme-volume.c			\
	acme-volume.h			\
	eggaccelerators.c		\
	eggaccelerators.h		\
	eggdesktopfile.c		\
	eggdesktopfile.h		\
	eggsmclient.c			\
	eggsmclient.h			\
	eggsmclient-private.h		\
	eggsmclient-xsmp.c		\
	gsm-app.c			\
	gsm-app.h			\
	gsm-client.c			\
	gsm-client.h			\
	gsm-client-xsmp.c		\
	gsm-client-xsmp.h		\
	gsm-session.c			\
	gsm-session.h			\
	gsm-xsmp.c			\
	gsm-xsmp.h			\
	sugar-grid.c			\
	sugar-grid.h			\
	sugar-cursor-tracker.c		\
	sugar-cursor-tracker.h		\
	sugar-gesture-grabber.c		\
	sugar-gesture-grabber.h		\
	sugar-key-grabber.c		\
	sugar-key-grabber.h		\
	sugar-wm.c			\
	sugar-wm.h

sugar_LTLIBRARIES = _sugarbaseext.la

_sugarbaseext_la_CFLAGS = 		\
	-DXDG_PREFIX=sugar_mime		\
	$(WARN_CFLAGS)			\
	$(EXT_CFLAGS)		\
	$(PYTHON_INCLUDES)

BUILT_SOURCES = 			\
	sugar-marshal.c			\
	sugar-marshal.h

_sugarbaseext_la_LDFLAGS = -module -avoid-version
_sugarbaseext_la_LIBADD = $(EXT_LIBS)
_sugarbaseext_la_SOURCES = 	\
	_sugarbaseextmodule.c	\
	xdgmime.c 		\
	xdgmime.h		\
	xdgmimealias.c		\
	xdgmimealias.h		\
	xdgmimecache.c		\
	xdgmimecache.h		\
	xdgmimeglob.c 		\
	xdgmimeglob.h 		\
	xdgmimeint.c 		\
	xdgmimeint.h 		\
	xdgmimemagic.c  	\
	xdgmimemagic.h		\
	xdgmimeparent.c		\
	xdgmimeparent.h

nodist__sugarbaseext_la_SOURCES = _sugarbaseext.c

_sugarbaseext.c: _sugarbaseext.defs _sugarbaseext.override

.defs.c:
	(cd $(srcdir)\
	 && $(PYGTK_CODEGEN) \
	    --override $*.override \
	    --prefix py$* $*.defs) > gen-$*.c \
	&& cp gen-$*.c $*.c \
	&& rm -f gen-$*.c

sugar-marshal.c: sugar-marshal.list
	$(GLIB_GENMARSHAL) --prefix=sugar_marshal \
		$(srcdir)/sugar-marshal.list --header --body > sugar-marshal.c

sugar-marshal.h: sugar-marshal.list
	$(GLIB_GENMARSHAL) --prefix=sugar_marshal \
		$(srcdir)/sugar-marshal.list --header > sugar-marshal.h

CLEANFILES = $(BUILT_SOURCES) _sugarbaseext.c
EXTRA_DIST = sugar-marshal.list _sugarbaseext.override _sugarbaseext.defs

-include $(INTROSPECTION_MAKEFILE)
INTROSPECTION_GIRS = SugarExt-1.0.gir
INTROSPECTION_SCANNER_ARGS = --identifier-prefix=Sugar --symbol-prefix=sugar \
	--identifier-prefix=EggSM --symbol-prefix=egg_sm \
	--identifier-prefix=Gsm --symbol-prefix=gsm \
	--identifier-prefix=Acme --symbol-prefix=acme \
	--include-uninstalled=$(top_builddir)/src/sugar3/event-controller/SugarGestures-1.0.gir
INTROSPECTION_COMPILER_ARGS = --includedir=$(top_builddir)/src/sugar3/event-controller
SugarExt_1_0_gir_LIBS = libsugarext.la $(top_builddir)/src/sugar3/event-controller/libsugar-eventcontroller.la
SugarExt_1_0_gir_FILES = \
	acme-volume.c \
	acme-volume.h \
	acme-volume-alsa.c \
	acme-volume-alsa.h \
	eggsmclient.c \
	eggsmclient.h \
	eggsmclient-xsmp.c \
	eggsmclient-xsmp.h \
	gsm-session.c \
	gsm-session.h \
	gsm-xsmp.c \
	gsm-xsmp.h \
	sugar-cursor-tracker.c \
	sugar-cursor-tracker.h \
	sugar-gesture-grabber.c \
	sugar-gesture-grabber.h \
	sugar-key-grabber.c \
	sugar-key-grabber.h \
	sugar-grid.c \
	sugar-grid.h \
        sugar-wm.c    \
        sugar-wm.h

SugarExt_1_0_gir_INCLUDES = Gtk-3.0 Gdk-3.0
SugarExt_1_0_gir_PACKAGES = gtk+-3.0 gdk-3.0
SugarExt_1_0_gir_EXPORT_PACKAGES = SugarExt-1.0

girdir = $(datadir)/gir-1.0
gir_DATA = SugarExt-1.0.gir

typelibdir = $(libdir)/girepository-1.0
typelib_DATA = SugarExt-1.0.typelib

CLEANFILES += $(gir_DATA) $(typelib_DATA)
