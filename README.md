[![DOI](https://zenodo.org/badge/103197335.svg)](https://zenodo.org/badge/latestdoi/103197335)
[![Python 3.7](https://img.shields.io/badge/python-3.7-green.svg)](https://www.python.org/downloads/release/python-377/)
[![Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Build Status](https://travis-ci.org/Barski-lab/cwl-airflow.svg?branch=master)](https://travis-ci.org/Barski-lab/cwl-airflow)
[![Coverage Status](https://coveralls.io/repos/github/Barski-lab/cwl-airflow/badge.svg?branch=master)](https://coveralls.io/github/Barski-lab/cwl-airflow?branch=master)
[![Downloads](https://pepy.tech/badge/cwl-airflow)](https://pepy.tech/project/cwl-airflow)


# **CWL-Airflow**

Python package to extend **[Apache-Airflow 1.10.12](https://airflow.apache.org)**
functionality with **[CWL v1.1](https://www.commonwl.org/v1.1/)** support

## **Cite as**

Michael Kotliar, Andrey V Kartashov, Artem Barski, CWL-Airflow: a lightweight pipeline manager supporting Common Workflow Language, GigaScience, Volume 8, Issue 7, July 2019, giz084, https://doi.org/10.1093/gigascience/giz084

## **Get the latest version**
```
pip install cwl-airflow
```
Latest version [documentation](https://cwl-airflow.readthedocs.io/en/latest/)


## **Get published version**
```
pip install cwl-airflow==1.0.18
```
Published version [documentation](https://cwl-airflow.readthedocs.io/en/1.0.18/)

## **Notes**

When running on MacOS, you might need to set up the following env variable before starting `airflow scheduler/webserver`

```
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
```