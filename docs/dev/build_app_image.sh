#!/usr/bin/env bash

# get the latest appimagetool
wget -O appimagetool https://github.com/probonopd/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool

# create working directory
mkdir cwl-airflow.AppDir && cd cwl-airflow.AppDir

# create AppRun
echo '#!/bin/bash
APPDIR="$(dirname "$(readlink -e "$0")")"
export PATH="$APPDIR/usr/bin:$PATH"

if ! [ -z "${PYTHONHOME+_}" ] ; then
    unset PYTHONHOME
fi

if [ -n "${BASH-}" ] || [ -n "${ZSH_VERSION-}" ] ; then
    hash -r 2>/dev/null
fi

cwl-airflow ${@:1}' > AppRun
chmod +x AppRun

# create cwl-airflow.desktop
echo '[Desktop Entry]
Type=Application
Terminal=true
Exec=cwl-airflow --help
Name=CWL-Airflow
Icon=cwl-airflow
Categories=Utility;Science;
' > cwl-airflow.desktop

# copy icon file to working directory
cp ./cwl-airflow.png .

# install virtualenv in Python3
pip3 install virtualenv

# create virtual environment
mkdir usr
virtualenv --always-copy ./usr
source ./usr/bin/activate
# install cwl-airflow
pip install cwl-airflow
deactivate
virtualenv --relocatable ./usr
cd ..

# pack AppDir into AppImage
./appimagetool cwl-airflow.AppDir cwl-airflow