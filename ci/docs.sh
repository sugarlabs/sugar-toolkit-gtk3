#!/bin/bash

# Helper script to build documentation using Sphinx
# NOTE: Should only be run on archlinux:latest 

GREEN='\033[0;32m'
NC='\033[0m'

set -eux

show-green () {
    echo -e "${GREEN} ==> ${1} ${NC}" 
}

# build package from the AUR (arch user repository)
if command -v makepkg &> /dev/null
then
    show-green "Cloning sugar-toolkit-gtk3-git from AUR"
    mkdir .cache
    cd .cache 
    git clone https://aur.archlinux.org/sugar-toolkit-gtk3-git.git
    cd sugar-toolkit-gtk3-git
    makepkg -sif --noconfirm 
    show-green "Installing optional dependencies"
    yes | sudo pacman -S --needed $(cat .SRCINFO| grep 'optdepends' | grep -o '= .*:' | sed 's,= ,,g' | sed 's,:,,g') --noconfirm
    cd ../..
    show-green "Dependencies synced, packages built"

fi


# make source
show-green "Compiling"
./autogen.sh --with-python3
make

# make documentation
show-green "Building documentation"
./make-doc.sh
mkdir deploy
mv doc/_build/html deploy/sugar3
touch deploy/.nojekyll
# create an index.html so that users dont become confused
show-green "Writing index.html"
echo "<h1>Page Moved</h1>" > index.html
echo "<p>We have moved this page to <a href=\"https://github.com/sugarlabs/sugar-docs/blob/master/README.md\">GitHub</a>.</p>" >> index.html
echo "<p>How did you get here? Please <a href=\"https://github.com/sugarlabs/sugar-docs/issues\">report</a> any lingering links.</p>" >> index.html

show-green "Done"
