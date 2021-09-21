
############################################################################################################################
# Docker image for running CWL-Airflow conformance tests                                                                   #
############################################################################################################################
# Software:         CWL-Airflow                                                                                            #
# Software Version: CWL_AIRFLOW_VERSION                                                                                    #
# Image Version:    latest                                                                                                 #
# Description:      CWL-Airflow image for LocalExecutor and MYSQL backend                                                  #
# Website:          https://cwl-airflow.readthedocs.io/en/latest/                                                          #
# Provides:         Airflow, CWL-Airflow, cwltool                                                                          #
# Python:           PYTHON_VERSION                                                                                         #
# Base Image:       ubuntu:UBUNTU_VERSION                                                                                  #
# Build Cmd:        docker build --no-cache  --rm -t biowardrobe2/cwl-airflow:latest .                                     #
#   for tag:        docker build --no-cache --build-arg CWL_AIRFLOW_VERSION=[tag] --rm -t biowardrobe2/cwl-airflow:[tag] . #
############################################################################################################################

# can be provided through --build-arg PARAM=value
ARG UBUNTU_VERSION="20.04"
ARG PYTHON_VERSION="3.8.10"
ARG CWL_AIRFLOW_VERSION="master"

FROM ubuntu:${UBUNTU_VERSION}
LABEL maintainer="misha.kotliar@gmail.com"
ENV DEBIAN_FRONTEND noninteractive

WORKDIR /tmp

# ARG need to be declared after FROM statement again. See details below
# https://docs.docker.com/engine/reference/builder/#understand-how-arg-and-from-interact
ARG PYTHON_VERSION
ARG CWL_AIRFLOW_VERSION

ENV CWL_AIRFLOW_URL "https://github.com/Barski-lab/cwl-airflow"
ENV PYTHON_URL "https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz"

COPY ./scripts/start_webserver.sh /usr/local/bin/start_webserver.sh
COPY ./scripts/start_scheduler.sh /usr/local/bin/start_scheduler.sh
COPY ./scripts/start_apiserver.sh /usr/local/bin/start_apiserver.sh

RUN echo "Installing dependencies" && \
    apt-get update && \
    apt-get install -y gcc build-essential \
                       git wget curl zlib1g-dev libmysqlclient-dev libffi-dev libssl-dev \
                       ca-certificates \
                       nodejs mysql-client apt-transport-https libsqlite3-dev \
                       gnupg-agent software-properties-common && \
    echo "Installing Python" && \
    wget ${PYTHON_URL} && \
    tar xzf Python-${PYTHON_VERSION}.tgz && \
    cd Python-${PYTHON_VERSION} && \
    ./configure && \
    make && \
    make install && \
    cd .. && \
    echo "Installing docker-ce-cli" && \
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add - && \
    add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" && \
    apt-get update && \
    apt-get -y install docker-ce-cli && \
    echo "Installing cwl-airflow" && \
    pip3 install -U pip && \
    git clone ${CWL_AIRFLOW_URL} && \
    cd cwl-airflow && \
    git checkout ${CWL_AIRFLOW_VERSION} && \
    export SHORT_PYTHON_VERSION=$(echo ${PYTHON_VERSION} | cut -d "." -f 1,2) && \
    pip3 install ".[mysql]" --constraint ./packaging/constraints/constraints-${SHORT_PYTHON_VERSION}.txt && \
    cd .. && \
    echo "Cleaning up" && \
    apt-get clean && \
    apt-get purge && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /usr/share/doc/* && \
    strip /usr/local/bin/*; true