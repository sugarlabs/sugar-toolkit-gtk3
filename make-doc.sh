#!/bin/sh
set -e

if [ ! -d "src" ]; then
  echo "Error: ../src directory does not exist."
  exit 1
fi

if [ ! -d "doc" ]; then
  echo "Error: doc directory does not exist."
  exit 1
fi

sphinx-apidoc --force --separate --output-dir=doc src
make -C doc html
