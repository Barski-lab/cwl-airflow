
###############################################################################
# Software:         CWL-Airflow
# Software Version: 1.2.2
# Image Version:    0.0.1
# Description:      CWL-Airflow image for LocalExecutor and MYSQL backend
# Website:          https://cwl-airflow.readthedocs.io/en/latest/
# Provides:         Airflow, CWL-Airflow, cwltool
# Base Image:       ubuntu:18.04
# Build Cmd:        docker build --rm -t biowardrobe2/cwl-airflow:1.2.2-0.0.1 .
###############################################################################


FROM ubuntu:18.04
LABEL maintainer="misha.kotliar@gmail.com"
ENV DEBIAN_FRONTEND noninteractive

WORKDIR /tmp

ENV CWL_AIRFLOW_VERSION "1.2.2"

RUN apt-get update && \
    apt-get install -y nodejs python3-dev libmysqlclient-dev python3-pip gcc git wget curl && \
    pip3 install -U pip                                                                    && \
    pip3 install cwl-airflow[mysql]==${CWL_AIRFLOW_VERSION}                                && \
    apt-get clean                                                                          && \
    apt-get purge                                                                          && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /usr/share/doc/*                         && \
    strip /usr/local/bin/*; true