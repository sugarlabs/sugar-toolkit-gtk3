SUBDIRS = activity bundle clipboard graphics presence datastore

sugardir = $(pythondir)/sugar
sugar_PYTHON =		\
	env.py		\
        network.py	\
	profile.py	\
	session.py	\
	util.py		\
	wm.py

pkgpyexecdir = $(pythondir)/sugar

pkgpyexec_LTLIBRARIES = _sugarext.la

_sugarext_la_CFLAGS = 		\
	$(EXT_CFLAGS)		\
	$(PYTHON_INCLUDES)

_sugarext_la_LDFLAGS = -module -avoid-version
_sugarext_la_LIBADD = $(EXT_LIBS) -lSM -lICE

_sugarext_la_SOURCES =			\
	$(BUILT_SOURCES)		\
	_sugarextmodule.c		\
        app.h				\
	app.c				\
	client.h			\
	client.c			\
	client-xsmp.h			\
	client-xsmp.c			\
	eggaccelerators.c		\
	eggaccelerators.h		\
	eggdesktopfile.h		\
	eggdesktopfile.c		\
	eggsmclient.h			\
	eggsmclient.c			\
	eggsmclient-private.h		\
	eggsmclient-xsmp.c		\
	session.h			\
	session.c			\
	sexy-icon-entry.h		\
	sexy-icon-entry.c		\
	sugar-address-entry.c		\
	sugar-address-entry.h		\
	sugar-key-grabber.c		\
	sugar-key-grabber.h		\
	sugar-menu.h			\
	sugar-menu.c			\
	sugar-preview.h			\
	sugar-preview.c			\
	xsmp.h				\
	xsmp.c

BUILT_SOURCES = 			\
	_sugarext.c			\
	sugar-marshal.c			\
	sugar-marshal.h

_sugarext.c: _sugarext.defs _sugarext.override

.defs.c:
	(cd $(srcdir)\
	 && $(PYGTK_CODEGEN) \
	    --register $(PYGTK_DEFSDIR)/gdk-types.defs \
	    --register $(PYGTK_DEFSDIR)/gdk-types.defs \
	    --register $(PYGTK_DEFSDIR)/gtk-types.defs \
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

CLEANFILES = $(BUILT_SOURCES)
EXTRA_DIST = sugar-marshal.list _sugarext.defs _sugarext.override
