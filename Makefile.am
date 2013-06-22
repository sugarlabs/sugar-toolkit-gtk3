ACLOCAL_AMFLAGS = -I m4
DISTCHECK_CONFIGURE_FLAGS = --enable-introspection

DISTCLEANFILES =		\
	intltool-extract	\
	intltool-merge		\
	intltool-update

EXTRA_DIST =                    \
	intltool-merge.in       \
	intltool-update.in      \
	intltool-extract.in

SUBDIRS = bin src po

check: test
	pyflakes $(top_srcdir)
	pep8 $(top_srcdir)

test:
	python -m sugar3.test.discover $(top_srcdir)/tests
