#!/usr/bin/env bash

wget -O appimagetool https://github.com/probonopd/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool

pip3 install virtualenv
mkdir cwl-airflow.AppDir && cd cwl-airflow.AppDir

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

echo '[Desktop Entry]
Type=Application
Terminal=true
Exec=cwl-airflow --help
Name=CWL-Airflow
Icon=cwl-airflow
Categories=Utility;Science;
' > cwl-airflow.desktop

cp ./cwl-airflow.png .

mkdir usr
virtualenv --always-copy ./usr
source ./usr/bin/activate
pip install cwl-airflow
deactivate
virtualenv --relocatable ./usr
cd ..

./appimagetool cwl-airflow.AppDir cwl-airflow