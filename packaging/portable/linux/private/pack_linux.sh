#!/usr/bin/env bash

MANYLINUX_VERSION=$1      # This means that downloaded python version has been built in CentOS 7. See https://www.python.org/dev/peps/pep-0599/ for details.
PYTHON_VERSION=$2         # Three digits. Before build check the latest available versions on https://github.com/niess/python-appimage/tags
CWL_AIRFLOW_VERSION=$3    # Will be always pulled from GitHub. Doesn't support build from local directory

WORKING_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

echo "Packing CWL-Airflow ($CWL_AIRFLOW_VERSION) for Python ${PYTHON_VERSION}"
echo "Current working directory ${WORKING_DIR}"

SHORT_PYTHON_VERSION=$(echo ${PYTHON_VERSION} | cut -d "." -f 1,2)
SHORT_PYTHON_VERSION_MONO=$(echo ${PYTHON_VERSION} | cut -d "." -f 1,2 | tr -d ".")

PYTHON_URL="https://github.com/niess/python-appimage/releases/download/python${SHORT_PYTHON_VERSION}/python${PYTHON_VERSION}-cp${SHORT_PYTHON_VERSION_MONO}-cp${SHORT_PYTHON_VERSION_MONO}-manylinux${MANYLINUX_VERSION}_x86_64.AppImage"
PYTHON_APPIMAGE="python${PYTHON_VERSION}-cp${SHORT_PYTHON_VERSION_MONO}-cp${SHORT_PYTHON_VERSION_MONO}-manylinux${MANYLINUX_VERSION}_x86_64.AppImage"
CWL_AIRFLOW_URL="https://github.com/Barski-lab/cwl-airflow"

echo "Installing required dependencies through yum: wget git gcc"
yum install wget git gcc -y

echo "Creating build folder"
mkdir -p $WORKING_DIR/python3
cd $WORKING_DIR/python3

echo "Downloading and extracting Python ${PYTHON_VERSION} with --appimage-extract option"
wget $PYTHON_URL
chmod +x $PYTHON_APPIMAGE
./$PYTHON_APPIMAGE --appimage-extract
mv squashfs-root python${PYTHON_VERSION}
rm $PYTHON_APPIMAGE

echo "Cloning CWL-Airflow"
git clone $CWL_AIRFLOW_URL
cd cwl-airflow
echo "Switch to ${CWL_AIRFLOW_VERSION} branch/tag"
git checkout $CWL_AIRFLOW_VERSION

echo "Install CWL-Airflow using dependency constraints from constraints-${SHORT_PYTHON_VERSION}.txt"
../python${PYTHON_VERSION}/AppRun -m pip install ".[crypto,postgres]" --constraint ./packaging/constraints/constraints-${SHORT_PYTHON_VERSION}.txt
cd ..
rm -rf cwl-airflow

echo "Creating bin_portable folder"
mkdir -p ./bin_portable
cd ./python${PYTHON_VERSION}/opt/python${SHORT_PYTHON_VERSION}/bin

TEMPLATE='#!/bin/bash\nBASE_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )\nexport PATH="$BASE_DIR/python'$PYTHON_VERSION'/usr/bin":"$PATH"\n'

for file in .* *
do
    if [[ -f "$file" ]] && [[ -x "$file" ]]
    then
        echo "Process '$file'"
        echo -e $TEMPLATE > ../../../../bin_portable/$file
        echo "$file \"\$@\"" >> ../../../../bin_portable/$file
    else
        echo "Skip '$file'"
    fi
done
cd ../../../..
chmod +x ./bin_portable/*
cd ..

echo "Updating permissions to u+w for python3 folder"
chmod -R u+w python3

echo "Compressing relocatable Python ${PYTHON_VERSION} with installed CWL-Airflow ($CWL_AIRFLOW_VERSION) to tar.gz"
OUTPUT_NAME="python_${PYTHON_VERSION}_cwl_airflow_master_linux.tar.gz"
#"python_${PYTHON_VERSION}_cwl_airflow_${CWL_AIRFLOW_VERSION}_linux.tar.gz"
tar -zcf $OUTPUT_NAME python3
rm -rf python3