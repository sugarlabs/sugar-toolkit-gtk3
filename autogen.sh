#!/bin/sh
export ACLOCAL="aclocal -I m4"

intltoolize
autoreconf -i
./configure --enable-maintainer-mode "$@"
