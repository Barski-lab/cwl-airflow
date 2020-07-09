import os
import re
import hashlib
import pkg_resources
import json

from copy import deepcopy
from ruamel.yaml import YAML
from tempfile import mkdtemp
from shutil import rmtree
from urllib.parse import urlparse
from typing import MutableMapping, MutableSequence


def get_api_failure_reason(response):
    """
    Handy function to safely get a failure reason from
    the "detail" field of request.response object returned
    from our API
    """

    try:
        reason = response.json()["detail"]
    except (ValueError, KeyError):
        reason = "unknown reason"
    return reason


def remove_field_from_dict(data, key):
    """
    Returns data with all occurences of "key" removed.
    "data" should be a dictionary.
    """

    data_copy = deepcopy(data)

    def __clean(data, key):
        if isinstance(data, MutableMapping):
            if key in data:
                del data[key]
            for item in data:
                __clean(data[item], key)
        if isinstance(data, MutableSequence):
            for item in data:
                __clean(item, key)

    __clean(data_copy, key)

    return data_copy


def get_files(location, filename_pattern=None):
    """
    Recursively searches for files in a folder by regex pattern.
    Results for the files with the same basenames will be overwritten.
    """

    filename_pattern = ".*" if filename_pattern is None else filename_pattern
    files_dict = {}
    for root, dirs, files in os.walk(location):
        files_dict.update(
            {filename: os.path.join(root, filename) for filename in files if re.match(filename_pattern, filename)}
        )
    return files_dict


def get_dir(location, cwd=None, permissions=None, exist_ok=None):

    permissions = 0o0775 if permissions is None else permissions
    exist_ok = True if exist_ok is None else exist_ok
    cwd = os.getcwd() if cwd is None else cwd

    abs_location = get_absolute_path(location, cwd)
    try:
        os.makedirs(abs_location, mode=permissions)
    except os.error:
        if not exist_ok:
            raise
    return abs_location


def get_path_from_url(url):
    return urlparse(url).path


def get_absolute_path(p, cwd=None):
    """
    Get absolute path relative to cwd or current working directory
    """

    cwd = os.getcwd() if cwd is None else cwd

    return p if os.path.isabs(p) else os.path.normpath(os.path.join(cwd, p))


def get_rootname(location):
    return os.path.splitext(os.path.basename(location))[0]


def get_version():
    """
    Returns current version of the package if it's installed
    """

    pkg = pkg_resources.require("cwl_airflow")
    return pkg[0].version if pkg else "unknown version"


def get_md5_sum(location, block_size=2**20):
    md5_sum = hashlib.md5()
    url_path = get_path_from_url(location)                # need to get rid of file:// if it was url
    with open(url_path , "rb") as input_stream:  
        while True:
            buf = input_stream.read(block_size)
            if not buf:
                break
            md5_sum.update(buf)
    return md5_sum.hexdigest()


def load_yaml(location):
    """
    Tries to load yaml document from file or string.

    If file cannot be loaded, assumes that location
    is a string and tries to load yaml from string.

    If string wasn't parsed and YAML didn't raise
    YAMLError, check ir the parsed result is the same
    as input. If yes, raise ValueError
    """

    yaml = YAML()
    yaml.preserve_quotes = True
    try:
        with open(location, "r") as input_stream:
            data = yaml.load(input_stream)
    except (FileNotFoundError, OSError):           # catch OSError raised when "filename too long"
        data = yaml.load(location)
    if data == location:
        raise ValueError
    return data


def dump_json(data, location):                    # TODO: consider substitute it with dump_yaml for consistency
    with open(location , "w") as output_stream:
        json.dump(data, output_stream, indent=4)


class CleanAirflowImport():
    """
    Replaces AIRFLOW_HOME and AIRFLOW_CONFIG from os.environ
    with temporary values. On exit either restores the previous values
    or removes them from os.environ, and cleans temp directory.
    Useful when importing modules from Airflow, that silently create
    airflow folder. Note, all the changes are made only within Python.
    __suppress_logging and __restore_logging are used to prevent Airflow
    from printing deprecation warnings
    """


    def __enter__(self):
        self.__suppress_logging()
        self.backup_airflow_home = os.environ.get("AIRFLOW_HOME")
        self.backup_airflow_config = os.environ.get("AIRFLOW_CONFIG")
        self.temp_airflow_home = mkdtemp()
        os.environ["AIRFLOW_HOME"] = self.temp_airflow_home
        os.environ["AIRFLOW_CONFIG"] = os.path.join(self.temp_airflow_home, "airflow.cfg")


    def __exit__(self, type, value, traceback):
        rmtree(self.temp_airflow_home)

        if self.backup_airflow_home is not None:
            os.environ["AIRFLOW_HOME"] = self.backup_airflow_home
        else:
            del os.environ["AIRFLOW_HOME"]

        if self.backup_airflow_config is not None:
            os.environ["AIRFLOW_CONFIG"] = self.backup_airflow_config
        else:
            del os.environ["AIRFLOW_CONFIG"]

        self.__restore_logging()


    def __suppress_logging(self):
        self.NULL_FDS = [os.open(os.devnull, os.O_RDWR) for x in range(2)]
        self.BACKUP_FDS = os.dup(1), os.dup(2)
        os.dup2(self.NULL_FDS[0], 1)
        os.dup2(self.NULL_FDS[1], 2)


    def __restore_logging(self):
        os.dup2(self.BACKUP_FDS[0], 1)
        os.dup2(self.BACKUP_FDS[1], 2)
        os.close(self.NULL_FDS[0])
        os.close(self.NULL_FDS[1])