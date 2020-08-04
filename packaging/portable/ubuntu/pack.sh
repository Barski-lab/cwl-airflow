#!/usr/bin/env bash

UBUNTU_VERSION=${1:-"18.04"}
PYTHON_VERSION=${2:-"3.6"}
CWL_AIRFLOW_VERSION=${3:-"master"}

echo "Pack CWL-Airflow from $CWL_AIRFLOW_VERSION branch/tag for Python ${PYTHON_VERSION} in dockerized Ubuntu $UBUNTU_VERSION"
WORKING_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
docker run --rm -it -v ${WORKING_DIR}:/tmp/ubuntu ubuntu:${UBUNTU_VERSION} /tmp/ubuntu/private/run_inside_docker.sh ${PYTHON_VERSION} ${CWL_AIRFLOW_VERSION}