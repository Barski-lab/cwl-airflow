#!/usr/bin/env bash

PYTHON_VERSION=${1:-"3.8"}
CWL_AIRFLOW_VERSION=${2:-`git rev-parse --abbrev-ref HEAD`}      # Will be always pulled from GitHub. Doesn't support build from local directory

echo "Pack CWL-Airflow from $CWL_AIRFLOW_VERSION branch/tag for Python ${PYTHON_VERSION} in current macOS version"
PYTHON_URL="https://briefcase-support.s3.amazonaws.com/python/${PYTHON_VERSION}/macOS/Python-${PYTHON_VERSION}-macOS-support.b1.tar.gz"
CWL_AIRFLOW_URL="https://github.com/Barski-lab/cwl-airflow"
TEMPLATE='#!/bin/bash\nBASE_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )\nexport PYTHONPATH="$BASE_DIR/lib/python3.*/site-packages"\nexport PATH="$BASE_DIR/bin":"$PATH"'
WORKING_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

echo "Create build folder"
mkdir -p $WORKING_DIR/build
cd $WORKING_DIR/build

echo "Download and extract Python ${PYTHON_VERSION}"
mkdir python3
cd python3
wget -q --show-progress $PYTHON_URL
tar xzf Python-${PYTHON_VERSION}-macOS-support.b1.tar.gz
rm Python-${PYTHON_VERSION}-macOS-support.b1.tar.gz
if [ -e "bin" ]; then
  echo "No need to move extracted python"
else
    mv python/* .
    rm -rf python
fi

echo "Download and install latest pip"
curl -s https://bootstrap.pypa.io/get-pip.py -o get-pip.py
./bin/python3 get-pip.py > /dev/null
rm get-pip.py

echo "Clone CWL-Airflow"
git clone --quiet $CWL_AIRFLOW_URL
cd cwl-airflow
echo "Switch to ${CWL_AIRFLOW_VERSION} branch/tag"
git checkout --quiet $CWL_AIRFLOW_VERSION

echo "Install CWL-Airflow using dependency constraints from constraints-${PYTHON_VERSION}.txt, compile lxml"
../bin/pip3 install --prefix="../" --no-warn-script-location -qq ".[crypto,postgres]" --constraint ./packaging/constraints/constraints-${PYTHON_VERSION}.txt
../bin/pip3 uninstall -y -qq lxml
../bin/pip3 install --prefix="../" --no-warn-script-location --no-binary lxml -qq lxml  # otherwise cannot be properly signed
cd ..
rm -rf cwl-airflow

echo "Replace shebang for executable files in ./bin folder"
find ./bin -type f -maxdepth 1 -exec grep -Iq "^#\!.*python.*" {} \; -exec sed -i '' -e '1s/.*/#!\/usr\/bin\/env python3/' {}  \;

echo "Create bin_portable folder"
mkdir -p ./bin_portable
cd ./bin

for file in .* *
do
    if [[ -f "$file" ]] && [[ -x "$file" ]]
    then
        echo "Process '$file'"
        echo -e $TEMPLATE > ../bin_portable/$file
        echo "$file \"\$@\"" >> ../bin_portable/$file
    else
        echo "Skip '$file'"
    fi
done
chmod +x ../bin_portable/*
cd ../..

echo "Update permissions to u+w for python3 folder"
chmod -R u+w python3

echo "Compress relocatable python3 with installed CWL-Airflow to tar.gz"
# MACOS_VERSION=$( sw_vers | grep ProductVersion | cut -f 2 )
OUTPUT_NAME="python_${PYTHON_VERSION}_cwl_airflow_${CWL_AIRFLOW_VERSION}_macos"
tar -zcf $OUTPUT_NAME.tar.gz python3
rm -rf python3