
###############################################################################
# Software:         CWL-Airflow
# Software Version: always latest commit from master
# Image Version:    latest
# Description:      CWL-Airflow image for LocalExecutor and MYSQL backend
#                   using default Python 3.8
# Website:          https://cwl-airflow.readthedocs.io/en/latest/
# Provides:         Airflow, CWL-Airflow, cwltool
# Base Image:       ubuntu:20.04
# Build Cmd:        docker build --rm -t biowardrobe2/cwl-airflow:latest .
###############################################################################


FROM ubuntu:20.04
LABEL maintainer="misha.kotliar@gmail.com"
ENV DEBIAN_FRONTEND noninteractive

WORKDIR /tmp

ENV CWL_AIRFLOW_VERSION "master"
ENV CWL_AIRFLOW_URL "https://github.com/Barski-lab/cwl-airflow"

RUN apt-get update && \
    apt-get install -y python3-dev python3-pip nodejs gcc git wget curl libmysqlclient-dev  && \
    pip3 install -U pip                                                                     && \
    git clone ${CWL_AIRFLOW_URL}                                                            && \
    cd cwl-airflow                                                                          && \
    git checkout ${CWL_AIRFLOW_VERSION}                                                     && \
    pip3 install ".[mysql,crypto]" --constraint ./packaging/constraints/constraints-3.8.txt && \
    cd ..                                                                                   && \
    rm -rf cwl-airflow                                                                      && \
    apt-get clean                                                                           && \
    apt-get purge                                                                           && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /usr/share/doc/*                          && \
    strip /usr/local/bin/*; true