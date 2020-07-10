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
- python 3.6
- docker (follow the [link](https://docs.docker.com/install/linux/docker-ce/ubuntu/) to install Docker on Ubuntu)
- pip (follow the [link](https://pip.pypa.io/en/stable/installing/) to install the latest stable Pip)
- setuptools
  ```bash
  pip install -U setuptools --user
  ```

  `--user` - optional parameter to install all the packages into your *HOME* directory instead of the system Python
  directories. It will be helpful if you don't have enough permissions to install new Python packages.
  You might also need to update your *PATH* variable in order to have access to the installed packages (an easy
  way to do it is described in [Troubleshooting](./troubleshooting.md) section).
  If installing on macOS brewed Python `--user` **should not** be used (explained [here](https://docs.brew.sh/Homebrew-and-Python))

## Install cwl-airflow

```sh
$ pip install cwl-airflow --user
```
