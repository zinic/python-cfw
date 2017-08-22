#!/usr/bin/env bash

function qpushd { pushd $@ >> /dev/null 2>&1; }
function qpopd { popd >> /dev/null 2>&1; }

# Remove old stuff
if [ -d deb_dist ]; then
    rm -rf deb_dist
fi

# Invoke from Python3 to create the sources for debian
python3 setup.py --command-packages=stdeb.command sdist_dsc

# Move to where the new source archives are
qpushd $(find deb_dist -name 'cfw-*' -type d)

# Use dpkg-buildpackage and fakeroot to build the debian pkg
dpkg-buildpackage -rfakeroot -uc -us

# And we're done
qpopd
