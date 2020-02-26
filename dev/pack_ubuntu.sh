#!/usr/bin/env bash

# Run script in the current directory without any arguments
# NOTE: you should have python3, pip3, 2to3 and vitrualenv installed


# create directory for portable version of cwl-airflow
mkdir cwl-airflow
cd cwl-airflow


# create virtual environment
virtualenv -p `which python3` --always-copy .
source ./bin/activate


# install cwl-airflow
cd ../..
pip3 install .
cd ./dev/cwl-airflow
deactivate


# replace default path to python3
find ./bin -executable -type f -maxdepth 1 -exec grep -Iq "^#\!.*python.*" {} \; -exec sed -i '' -e '1s/.*/#!\/usr\/bin\/env python3/' {}  \;


# copy executable files
mkdir bin_portable
cp ../linux/* ./bin_portable


# Copy 2to3 manually which is not included in virtual environment by default
cp -r /usr/lib/python3.*/lib2to3 ./lib/python3.*/site-packages
cp -r /usr/bin/2to3 ./bin


# compress to tar.gz
cd ..
chmod -R u+w ./cwl-airflow
tar -zcvf cwl-airflow.ubuntu.tar.gz cwl-airflow
rm -rf cwl-airflow