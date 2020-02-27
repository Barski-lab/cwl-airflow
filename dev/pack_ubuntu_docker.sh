#!/usr/bin/env bash

BASE_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )
PYTHON_LINK=$1
PYTHON_VERSION=$2


apt-get update
apt-get install gcc git wget curl -y


mkdir $BASE_DIR/dev/cwl-airflow-ubuntu
cd $BASE_DIR/dev/cwl-airflow-ubuntu


wget $PYTHON_LINK
tar xzf Python-${PYTHON_VERSION}-linux-x86_64-support.b1.tar.gz
rm Python-${PYTHON_VERSION}-linux-x86_64-support.b1.tar.gz


curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
./bin/python3 get-pip.py
rm get-pip.py


./bin/pip3 install --prefix="." --no-warn-script-location --upgrade $BASE_DIR


find ./bin -executable -type f -maxdepth 1 -exec grep -Iq "^#\!.*python.*" {} \; -exec sed -i '' -e '1s/.*/#!\/usr\/bin\/env python3/' {}  \;


mkdir bin_portable
cp ../linux/* ./bin_portable


chmod -R u+w .


cd ..
tar -zcvf cwl-airflow.ubuntu.tar.gz cwl-airflow-ubuntu
rm -rf cwl-airflow-ubuntu










