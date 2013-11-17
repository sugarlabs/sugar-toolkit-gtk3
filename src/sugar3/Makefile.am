SUBDIRS = activity \
          bundle \
          event-controller \
          graphics \
          presence \
          datastore \
          dispatch \
          test

sugardir = $(pythondir)/sugar3
sugar_PYTHON =		\
	__init__.py	\
	env.py		\
	logger.py	\
	mime.py		\
        network.py	\
	profile.py	\
	util.py

nodist_sugar_PYTHON = config.py

XDG_MIME_SOURCES = \
	xdgmime.c \
        xdgmime.h \
        xdgmimealias.c \
        xdgmimealias.h \
        xdgmimecache.c \
        xdgmimecache.h \
        xdgmimeglob.c \
        xdgmimeglob.h \
        xdgmimeint.c \
        xdgmimeint.h \
        xdgmimemagic.c \
        xdgmimemagic.h \
        xdgmimeparent.c \
        xdgmimeparent.h

lib_LTLIBRARIES = libsugarext.la

libsugarext_la_CFLAGS = \
	-DHAVE_ALSA \
	-DXDG_PREFIX=sugar_mime \
	$(EXT_CFLAGS) \
	$(WARN_CFLAGS)

libsugarext_la_LDFLAGS = $(LDADD)
libsugarext_la_LIBADD = $(EXT_LIBS)

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
	eggsmclient-xsmp.h 		\
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
	sugar-fatattr.c			\
	sugar-fatattr.h			\
	sugar-grid.c			\
	sugar-grid.h			\
	sugar-cursor-tracker.c		\
	sugar-cursor-tracker.h		\
	sugar-gesture-grabber.c		\
	sugar-gesture-grabber.h		\
	sugar-key-grabber.c		\
	sugar-key-grabber.h		\
	sugar-wm.h			\
	sugar-wm.c			\
	sugar-gconf.h       		\
	sugar-gconf.c       		\
	$(XDG_MIME_SOURCES)

BUILT_SOURCES = 			\
	sugar-marshal.c			\
	sugar-marshal.h

sugar-marshal.c: sugar-marshal.list
	$(GLIB_GENMARSHAL) --prefix=sugar_marshal \
		$(srcdir)/sugar-marshal.list --header --body > sugar-marshal.c

sugar-marshal.h: sugar-marshal.list
	$(GLIB_GENMARSHAL) --prefix=sugar_marshal \
		$(srcdir)/sugar-marshal.list --header > sugar-marshal.h

CLEANFILES = $(BUILT_SOURCES)
EXTRA_DIST = sugar-marshal.list

-include $(INTROSPECTION_MAKEFILE)
INTROSPECTION_GIRS = SugarExt-1.0.gir
INTROSPECTION_SCANNER_ARGS = \
	-D XDG_PREFIX=sugar_mime \
        --identifier-prefix=Sugar --symbol-prefix=sugar \
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
	sugar-fatattr.c	\
	sugar-fatattr.h	\
	sugar-cursor-tracker.c \
	sugar-cursor-tracker.h \
	sugar-gesture-grabber.c \
	sugar-gesture-grabber.h \
	sugar-key-grabber.c \
	sugar-key-grabber.h \
	sugar-grid.c \
	sugar-grid.h \
    sugar-wm.c \
    sugar-wm.h \
    sugar-gconf.c \
    sugar-gconf.h \
	$(XDG_MIME_SOURCES)

SugarExt_1_0_gir: libsugarext.la
SugarExt_1_0_gir_INCLUDES = Gtk-3.0 Gdk-3.0 GConf-2.0
SugarExt_1_0_gir_PACKAGES = gtk+-3.0 gdk-3.0 gconf-2.0
SugarExt_1_0_gir_EXPORT_PACKAGES = SugarExt-1.0

girdir = $(datadir)/gir-1.0
gir_DATA = SugarExt-1.0.gir

typelibdir = $(libdir)/girepository-1.0
typelib_DATA = SugarExt-1.0.typelib

CLEANFILES += $(gir_DATA) $(typelib_DATA)
