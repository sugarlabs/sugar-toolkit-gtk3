#!/bin/sh
set -e

# Use absolute paths to avoid directory traversal issues and ambiguity
REPO_ROOT=$(pwd)
SRC_DIR="$REPO_ROOT/src/sugar3"
DOC_DIR="$REPO_ROOT/doc"

echo "Building documentation..."
echo "Repository Root: $REPO_ROOT"
echo "Source Directory: $SRC_DIR"
echo "Doc Directory: $DOC_DIR"

# Debug contents
# ls -la "$REPO_ROOT"

if [ ! -d "$SRC_DIR" ]; then
    echo "Error: Source directory $SRC_DIR does not exist."
    ls -la src
    exit 1
fi

if [ ! -d "$DOC_DIR" ]; then
    echo "Error: Doc directory $DOC_DIR does not exist."
    ls -la
    exit 1
fi

# Run sphinx-apidoc outputting to doc directory
echo "Running sphinx-apidoc..."
sphinx-apidoc --force --separate -o "$DOC_DIR" "$SRC_DIR"

# Run make html from the doc directory using -C
echo "Running make html..."
make -C "$DOC_DIR" html
