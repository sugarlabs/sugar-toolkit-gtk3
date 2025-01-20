#!/bin/sh

sphinx-apidoc --force --separate --output-dir=doc ../src
make -C doc html