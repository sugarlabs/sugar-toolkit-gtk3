#!/bin/bash

# Helper script to build documentation using Sphinx
# NOTE: Should only be run on archlinux:latest 

GREEN='\033[0;32m'
NC='\033[0m'

set -eux

show-green () {
    echo -e "${GREEN} ==> ${1} ${NC}" 
}

# make source
show-green "Compiling"
sudo ./autogen.sh --with-python3
sudo make

# make documentation
show-green "Building documentation"
sudo ./make-doc.sh
sudo mkdir deploy
sudo mv doc/_build/html deploy/sugar3
sudo touch deploy/.nojekyll
# create an index.html so that users don't become confused
show-green "Writing index.html"
sudo echo "<h1>Page Moved</h1>" > deploy/index.html
sudo echo "<p>We have moved this page to <a href=\"https://github.com/sugarlabs/sugar-docs/blob/master/README.md\">GitHub</a>.</p>" >> deploy/index.html
sudo echo "<p>How did you get here? Please <a href=\"https://github.com/sugarlabs/sugar-docs/issues\">report</a> any lingering links.</p>" >> deploy/index.html

show-green "Done"
