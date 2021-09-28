[![DOI](https://zenodo.org/badge/103197335.svg)](https://zenodo.org/badge/latestdoi/103197335)
[![Python 3.7](https://img.shields.io/badge/python-3.7-green.svg)](https://www.python.org/downloads/release/python-377/)
[![Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Build Status](https://app.travis-ci.com/Barski-lab/cwl-airflow.svg?branch=master)](https://app.travis-ci.com/Barski-lab/cwl-airflow)
[![Coverage Status](https://coveralls.io/repos/github/Barski-lab/cwl-airflow/badge.svg?branch=master&service=github)](https://coveralls.io/github/Barski-lab/cwl-airflow?branch=master)
[![Downloads](https://pepy.tech/badge/cwl-airflow)](https://pepy.tech/project/cwl-airflow)


# **CWL-Airflow**

Python package to extend **[Apache-Airflow 2.1.4](https://airflow.apache.org)**
functionality with **[CWL v1.1](https://www.commonwl.org/v1.1/)** support

## **Cite as**

Michael Kotliar, Andrey V Kartashov, Artem Barski, CWL-Airflow: a lightweight pipeline manager supporting Common Workflow Language, GigaScience, Volume 8, Issue 7, July 2019, giz084, https://doi.org/10.1093/gigascience/giz084

## **Get the latest version**
```
export PYTHON_VERSION=`python3 --version | cut -d " " -f 2 | cut -d "." -f 1,2`
pip3 install cwl-airflow --constraint https://raw.githubusercontent.com/Barski-lab/cwl-airflow/master/packaging/constraints/constraints-${PYTHON_VERSION}.txt
```
Latest version [documentation](https://cwl-airflow.readthedocs.io/en/latest/)


## **Get published version**
```
pip install cwl-airflow==1.0.18
```
Published version [documentation](https://cwl-airflow.readthedocs.io/en/1.0.18/)

## **Notes**
Notes for developers can be found in [DEV README](https://github.com/Barski-lab/cwl-airflow/blob/master/README.dev.md)
