#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

pip3 install -r $DIR/../../test_requirements.txt

pytest --cov=cwl_airflow --cov-append --forked $DIR/test_conformance.py && \  
pytest --cov=cwl_airflow --cov-append --forked $DIR/test_helpers.py && \
pytest --cov=cwl_airflow --cov-append --forked $DIR/test_parser.py && \
pytest --cov=cwl_airflow --cov-append --forked $DIR/test_init_config.py && \
pytest --cov=cwl_airflow --cov-append --forked $DIR/test_cwl.py