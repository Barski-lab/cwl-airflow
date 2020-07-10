# How to install

## Requirements

### Ubuntu 16.04.4 (Xenial Xerus)

- python 2.7 or 3.5 (tested on the system Python 2.7.12 and 3.5.2)
- docker (follow the [link](https://docs.docker.com/install/linux/docker-ce/ubuntu/) to install Docker on Ubuntu)

  **Don't forget** to add your user to the *docker* group and then
  to log out and log back in so that your group membership is re-evaluated.
- python-dev (or python3-dev if using Python 3.5)
  ```bash
  sudo apt-get install python-dev # python3-dev
  ```
  *python-dev* is required in case your system needs to compile some python
  packages during the installation. We have built python *wheels* for most of such packages
  and provided them through *--find-links* argument while installing *cwl-airflow*.
  Nevertheless in case of installation problems you might still be required to install
  this dependency.

### macOS 10.13.5 (High Sierra)

- python 2.7 or 3.6 (tested on the system Python 2.7.10 and brewed Python 2.7.15 / 3.6.5; **3.7.0 is not supported**)
- docker (follow the [link](https://docs.docker.com/docker-for-mac/install/) to install Docker on Mac)
- Apple Command Line Tools
  ```bash
  xcode-select --install
  ```
  Click *Install* on the pop up window when it appears, follow the instructions. *Apple Command Line Tools* are required in
  case your system needs to compile some python packages during the installation. We have built python wheels for most
  of such packages and provided them through *--find-links* argument while installing *cwl-airflow*. Nevertheless in case
  of installation problems you might still be required to install this dependency.

### Both Ubuntu and macOS

- pip (follow the [link](https://pip.pypa.io/en/stable/installing/) to install the latest stable Pip)

  Consider using `--user` if you encounter permission problems

- setuptools (tested on setuptools 40.0.0)
  ```bash
  pip install -U setuptools # --user
  ```

  `--user` - optional parameter to install all the packages into your *HOME* directory instead of the system Python
  directories. It will be helpful if you don't have enough permissions to install new Python packages.
  You might also need to update your *PATH* variable in order to have access to the installed packages (an easy
  way to do it is described in [Troubleshooting](./troubleshooting.md) section).
  If installing on macOS brewed Python `--user` **should not** be used (explained [here](https://docs.brew.sh/Homebrew-and-Python))

## Install cwl-airflow

```sh
$ pip install cwl-airflow --find-links https://michael-kotliar.github.io/cwl-airflow-wheels/ # --user
```
`--find-links` - using pre-compiled wheels from [Cwl-Airflow-Wheels](https://michael-kotliar.github.io/cwl-airflow-wheels/) repository
allows to avoid installing *Xcode* for macOS users and *python[3]-dev* for Ubuntu users
