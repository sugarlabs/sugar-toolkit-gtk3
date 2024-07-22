#!/bin/sh

echo "print files"
pwd
ls -l src/

sphinx-apidoc --force --separate --output-dir=doc src
make -C doc html
