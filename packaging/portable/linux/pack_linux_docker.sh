#!/usr/bin/env bash

CENTOS_VERSION=${1:-"7"}                                     # Shouldn't influence on the results. We need it only to unpack AppImage. Better to keep 7 for manylinux2014
MANYLINUX_VERSION=${2:-"2014"}                               # This means that downloaded python version has been built in CentOS 7. See https://www.python.org/dev/peps/pep-0599/ for details.
PYTHON_VERSION=${3:-"3.8.12"}                                # Three digits. Before build check the latest available versions on https://github.com/niess/python-appimage/tags
CWL_AIRFLOW_VERSION=${4:-`git rev-parse --abbrev-ref HEAD`}  # Will be always pulled from GitHub. Doesn't support build from local directory

WORKING_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
echo "Packing CWL-Airflow ($CWL_AIRFLOW_VERSION) for Python ${PYTHON_VERSION} in dockerized Centos $CENTOS_VERSION"
echo "Current working directory ${WORKING_DIR}"
echo "Staring centos:${CENTOS_VERSION} docker container"
docker run --rm -it -v ${WORKING_DIR}:/tmp/build centos:${CENTOS_VERSION} /tmp/build/private/pack_linux.sh ${MANYLINUX_VERSION} ${PYTHON_VERSION} ${CWL_AIRFLOW_VERSION}