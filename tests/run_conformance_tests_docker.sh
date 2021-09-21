#!/bin/bash
UBUNTU_VERSION=${1:-"20.04"}
PYTHON_VERSION=${2:-"3.8.10"}
CWL_AIRFLOW_VERSION=${3:-`git rev-parse --abbrev-ref HEAD`}
REPO_URL=${4:-"https://github.com/datirium/workflows.git"}
SUITE=${5:-"tests/conformance_tests.yaml"}

echo "Running tests for ${REPO_URL} from the file ${SUITE} with CWL-Airflow (${CWL_AIRFLOW_VERSION})"
echo "using Ubuntu ${UBUNTU_VERSION} and Python ${PYTHON_VERSION}"
./conformance_tests/run_conformance_tests.sh ${UBUNTU_VERSION} ${PYTHON_VERSION} ${CWL_AIRFLOW_VERSION} ${REPO_URL} ${SUITE}