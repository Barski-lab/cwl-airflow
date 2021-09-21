#!/bin/bash
UBUNTU_VERSION=${1:-"20.04"}
PYTHON_VERSION=${2:-"3.8.10"}
CWL_AIRFLOW_VERSION=${3:-`git rev-parse --abbrev-ref HEAD`}

WORKING_DIR=$( cd ../"$( dirname "${BASH_SOURCE[0]}" )" && pwd )
echo "Running unit tests with Python ${PYTHON_VERSION} in dockerized Ubuntu $UBUNTU_VERSION"
echo "Using CWL-Airflow (${CWL_AIRFLOW_VERSION})"
echo "Working directory $WORKING_DIR"
docker rmi cwl_airflow:latest --force
docker build --no-cache --build-arg UBUNTU_VERSION=$UBUNTU_VERSION \
                        --build-arg PYTHON_VERSION=$PYTHON_VERSION \
                        --build-arg CWL_AIRFLOW_VERSION=$CWL_AIRFLOW_VERSION \
                        --rm -t cwl_airflow:latest $WORKING_DIR/packaging/docker_compose/local_executor/cwl_airflow
docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock \
                    -v ${WORKING_DIR}:${WORKING_DIR} \
                    --workdir ${WORKING_DIR} \
                    cwl_airflow:latest \
                    ${WORKING_DIR}/tests/unit_tests/run_unit_tests.sh