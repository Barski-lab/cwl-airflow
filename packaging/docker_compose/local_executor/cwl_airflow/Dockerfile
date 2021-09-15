
###############################################################################
# Software:         CWL-Airflow
# Software Version: always latest commit from master
# Image Version:    latest
# Description:      CWL-Airflow image for LocalExecutor and MYSQL backend
#                   using default Python 3.8
# Website:          https://cwl-airflow.readthedocs.io/en/latest/
# Provides:         Airflow, CWL-Airflow, cwltool
# Base Image:       ubuntu:20.04
# Build Cmd:        docker build --no-cache  --rm -t biowardrobe2/cwl-airflow:latest .
#   for tag:        docker build --no-cache --build-arg CWL_AIRFLOW_VERSION=tag --rm -t biowardrobe2/cwl-airflow:latest .
###############################################################################

# can be provided through --build-arg CWL_AIRFLOW_VERSION=branch or tag
ARG CWL_AIRFLOW_VERSION="master"

FROM ubuntu:20.04
LABEL maintainer="misha.kotliar@gmail.com"
ENV DEBIAN_FRONTEND noninteractive

WORKDIR /tmp

# ARG need to be declared after FROM statement again. See details below
# https://docs.docker.com/engine/reference/builder/#understand-how-arg-and-from-interact
ARG CWL_AIRFLOW_VERSION

ENV CWL_AIRFLOW_URL "https://github.com/Barski-lab/cwl-airflow"
COPY ./scripts/start_webserver.sh /usr/local/bin/start_webserver.sh
COPY ./scripts/start_scheduler.sh /usr/local/bin/start_scheduler.sh
COPY ./scripts/start_apiserver.sh /usr/local/bin/start_apiserver.sh

RUN echo "Building ${CWL_AIRFLOW_VERSION} version of CWL-Airflow" && \
    apt-get update && \
    # installing dependencies (including docker dependencies)
    apt-get install -y python3-dev python3-pip nodejs gcc git wget curl \
                       libmysqlclient-dev mysql-client apt-transport-https \
                       ca-certificates gnupg-agent software-properties-common && \
    # installing docker-ce-cli
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add - && \
    add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" && \
    apt-get update && \
    apt-get -y install docker-ce-cli && \
    # installing cwl-airflow
    pip3 install -U pip                                                                     && \
    git clone ${CWL_AIRFLOW_URL}                                                            && \
    cd cwl-airflow                                                                          && \
    git checkout ${CWL_AIRFLOW_VERSION}                                                     && \
    pip3 install ".[mysql]" --constraint ./packaging/constraints/constraints-3.8.txt && \
    cd ..                                                                                   && \
    rm -rf cwl-airflow                                                                      && \
    # cleaning up
    apt-get clean                                                                           && \
    apt-get purge                                                                           && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /usr/share/doc/*                          && \
    strip /usr/local/bin/*; true