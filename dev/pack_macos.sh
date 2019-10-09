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
tar -zcvf cwl-airflow.macos.tar.gz cwl-airflow.app
rm -rf cwl-airflow.app
cd ..
rm -rf build_venv