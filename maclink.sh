#!/bin/sh
SUBLIME=~/Library/Application\ Support/Sublime\ Text\ 2
PWD=`pwd`
echo ls ${SUBLIME}

ln -s "/Applications/Sublime Text 2.app/Contents/SharedSupport/bin/subl" /usr/local/bin/sublime

ln -s -f "${PWD}/Data/Packages" "${SUBLIME}"
ln -s -f "${PWD}/Data/Installed Packages" "${SUBLIME}"
