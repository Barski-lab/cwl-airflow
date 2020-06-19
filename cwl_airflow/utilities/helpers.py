import os
import hashlib
import pkg_resources

from tempfile import mkdtemp
from shutil import rmtree


def get_dir(dir, cwd=None, permissions=None, exist_ok=None):

    permissions = 0o0775 if permissions is None else permissions
    exist_ok = True if exist_ok is None else exist_ok
    cwd = os.getcwd() if cwd is None else cwd

    abs_dir = get_absolute_path(dir, cwd)
    try:
        os.makedirs(abs_dir, mode=permissions)
    except os.error:
        if not exist_ok:
            raise
    return abs_dir


def get_absolute_path(p, cwd=None):
    """
    Get absolute path relative to cwd or current working directory
    """

    cwd = os.getcwd() if cwd is None else cwd

    return p if os.path.isabs(p) else os.path.normpath(os.path.join(cwd, p))


def get_version():
    """
    Returns current version of the package if it's installed
    """

    pkg = pkg_resources.require("cwl_airflow")
    return pkg[0].version if pkg else "unknown version"


def get_md5_sum(location, block_size=2**20):
    md5_sum = hashlib.md5()
    with open(location , "rb") as input_stream:
        while True:
            buf = input_stream.read(block_size)
            if not buf:
                break
            md5_sum.update(buf)
    return md5_sum.hexdigest()


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