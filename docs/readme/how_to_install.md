# How to install

## Install requirements

### Ubuntu 18.04.4 (Bionic Beaver)

- python3-dev
  ```bash
  sudo apt-get install python3-dev
  ```

### macOS 11.0.1 (Big Sur)

- Apple Command Line Tools
  ```bash
  xcode-select --install
  ```

### Both Ubuntu and macOS
- python 3.6 / 3.7 / 3.8
- docker (follow the [installation guides](https://docs.docker.com/engine/install/))
- pip (follow the [installation guides](https://pip.pypa.io/en/stable/installing/))
- setuptools
  ```bash
  pip3 install -U setuptools
  ```

## Install CWL-airflow

```sh
$ pip3 install cwl-airflow \
--constraint "https://raw.githubusercontent.com/Barski-lab/cwl-airflow/master/packaging/constraints/constraints-3.7.txt"
```
When using optional `--constraint` parameter you can limit dependencies to those versions that were tested with your Python.

Optionally, extra dependencies can be provided by adding `[mysql,celery,statsd]` at the end of the command above.
- **mysql** - enables MySQL server support
- **celery** - enables Celery cluster support
- **statsd** - enables StatsD metrics support

## Download portable version of CWL-airflow

Alternatively to installation, the relocatable standalone **Python3 with pre-installed CWL-Airfow** can be downloaded from the [Releases](https://github.com/Barski-lab/cwl-airflow/releases) section on GitHub.

**Note**, these are **not** cross-platform packages, so the version of OS should be the same as mentioned in the name of the file.
When extracted from archive, all executables can be found in the `python3/bin_portable` folder.

Similar packages for other versions of Ubuntu, Python and CWL-Airflow can be generated with the following commands:

```sh
# Ubuntu
# defaults: Ubuntu 18.04, Python 3.6, CWL-Airflow master branch

$ ./packaging/portable/ubuntu/pack.sh [UBUNTU_VERSION] [PYTHON_VERSION] [CWL_AIRFLOW_VERSION]

# macOS
# package is always built for current macOS version
# defaults: Python 3.8, CWL-Airflow master branch

$ ./packaging/portable/macos/pack.sh [PYTHON_VERSION] [CWL_AIRFLOW_VERSION]
```