# How to install

## Install requirements

### Ubuntu 18.04.4 (Bionic Beaver)

- python3-dev
  ```bash
  sudo apt-get install python3-dev
  ```

### macOS 10.15.3 (Catalina)

- Apple Command Line Tools
  ```bash
  xcode-select --install
  ```

### Both Ubuntu and macOS
- python 3.7
- docker (follow the [installation guides](https://docs.docker.com/engine/install/))
- pip (follow the [installation guides](https://pip.pypa.io/en/stable/installing/))
- setuptools
  ```bash
  pip3 install -U setuptools
  ```

## Install CWL-airflow

```sh
$ pip3 install cwl-airflow
```
Optionally, extra dependencies can be provided by adding `[mysql,celery,statsd]` at the end of the command above.
- **mysql** - enables MySQL server support
- **celery** - enables Celery cluster support
- **statsd** - enables StatsD metrics support

## Download portable version of CWL-airflow

Alternatively to installation, the relocatable standalone **Python3 with pre-installed CWL-Airfow** can be downloaded from the following links:

- [python_3.6_with_cwl_airflow_1.2.2_ubuntu_18.04.tar.gz](https://github.com/Barski-lab/cwl-airflow/releases/download/1.2.2/python_3.6_with_cwl_airflow_1.2.2_ubuntu_18.04.tar.gz)
- [python_3.7_with_cwl_airflow_1.2.2_macos_10.15.3.tar.gz](https://github.com/Barski-lab/cwl-airflow/releases/download/1.2.2/python_3.7_with_cwl_airflow_1.2.2_macos_10.15.3.tar.gz)

**Note**, these are **not** cross-platform packages, so the version of OS should be the same as mentioned in the name of the file.
When extracted from archive, all executables can be found in the `python3/bin_portable` folder.

Similar packages for other versions of Ubuntu, Python and CWL-Airflow can be generated with the following commands:

```sh
# Ubuntu
# defaults: Ubuntu 18.04, Python 3.6, CWL-Airflow master branch

$ ./packaging/portable/ubuntu/pack.sh [UBUNTU_VERSION] [PYTHON_VERSION] [CWL_AIRFLOW_VERSION]

# macOS
# package is always built for current macOS version
# defaults: Python 3.7, CWL-Airflow master branch

$ ./packaging/portable/macos/pack.sh [PYTHON_VERSION] [CWL_AIRFLOW_VERSION]
```