#!/usr/bin/env bash

UBUNTU_VERSION="18.04"
PYTHON_VERSION="3.6"

PYTHON_LINK="https://briefcase-support.s3.amazonaws.com/python/${PYTHON_VERSION}/linux/x86_64/Python-${PYTHON_VERSION}-linux-x86_64-support.b1.tar.gz"
BASE_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )

docker run --rm -it -v ${BASE_DIR}:/tmp/cwl-airflow ubuntu:${UBUNTU_VERSION} /tmp/cwl-airflow/dev/pack_ubuntu_docker.sh ${PYTHON_LINK} ${PYTHON_VERSION}