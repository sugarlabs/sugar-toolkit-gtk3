#!/bin/sh

echo "print files"
ls -l

sphinx-apidoc --force --separate --output-dir=doc src
make -C doc html
