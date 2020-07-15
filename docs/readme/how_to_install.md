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
