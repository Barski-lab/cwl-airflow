#!/usr/bin/env bash

UBUNTU_VERSION=${1:-"18.04"}          # Shouldn't influence on results. We need it to unpack AppImage
PYTHON_VERSION=${2:-"3.6.15"}         # Three digits. Check available versions on https://github.com/niess/python-appimage/tags
CWL_AIRFLOW_VERSION=${3:-"master"}    # Will be always pulled from GitHub. Do not build from local directory

WORKING_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
echo "Packing CWL-Airflow ($CWL_AIRFLOW_VERSION) for Python ${PYTHON_VERSION} in dockerized Ubuntu $UBUNTU_VERSION"
echo "Current working directory ${WORKING_DIR}"
echo "Staring ubuntu:${UBUNTU_VERSION} docker container"

docker run --rm -it -v ${WORKING_DIR}:/tmp/build ubuntu:${UBUNTU_VERSION} /tmp/build/private/pack_linux.sh ${PYTHON_VERSION} ${CWL_AIRFLOW_VERSION}