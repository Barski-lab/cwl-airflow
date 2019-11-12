#!/usr/bin/env bash
mkdir build_venv
cd build_venv
virtualenv .
source ./bin/activate
pip install briefcase
pip install --pre toga==0.3.0.dev14
cd ..
python setup.py macos
deactivate
cd macOS
cp ../dev/macos/*  ./cwl-airflow.app/Contents/MacOS/

find ./cwl-airflow.app/Contents/Resources/app/bin -type f -maxdepth 1 -exec sed -i '' -e '1s/.*/#!\/usr\/bin\/env python3/' {}  \;
find ./cwl-airflow.app/Contents/Resources/app_packages/bin -type f -maxdepth 1 -exec sed -i '' -e '1s/.*/#!\/usr\/bin\/env python3/' {}  \;

chmod -R u+w ./cwl-airflow.app
tar -zcvf cwl-airflow.macos.tar.gz cwl-airflow.app
rm -rf cwl-airflow.app
cd ..
rm -rf build_venv