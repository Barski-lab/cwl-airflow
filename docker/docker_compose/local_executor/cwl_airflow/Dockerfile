
###############################################################################
# Software:         CWL-Airflow
# Software Version: latest commit from master
# Image Version:    0.0.1
# Description:      CWL-Airflow image for LocalExecutor and MYSQL backend
# Website:          https://cwl-airflow.readthedocs.io/en/latest/
# Provides:         Airflow, CWL-Airflow, cwltool
# Base Image:       ubuntu:18.04
# Build Cmd:        docker build --rm -t biowardrobe2/cwl-airflow:latest .
###############################################################################


FROM ubuntu:18.04
LABEL maintainer="misha.kotliar@gmail.com"
ENV DEBIAN_FRONTEND noninteractive

WORKDIR /tmp

ENV CWL_AIRFLOW_VERSION "master"
ENV CWL_AIRFLOW_URL "https://github.com/Barski-lab/cwl-airflow"

RUN apt-get update && \
    apt-get install -y nodejs python3-dev libmysqlclient-dev python3-pip gcc git wget curl && \
    pip3 install -U pip                                                                    && \
    git clone ${CWL_AIRFLOW_URL}                                                           && \
    cd cwl-airflow                                                                         && \
    git checkout ${CWL_AIRFLOW_VERSION}                                                    && \
    pip3 install ".[mysql]"                                                                && \
    cd ..                                                                                  && \
    rm -rf cwl-airflow                                                                     && \
    apt-get clean                                                                          && \
    apt-get purge                                                                          && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /usr/share/doc/*                         && \
    strip /usr/local/bin/*; true