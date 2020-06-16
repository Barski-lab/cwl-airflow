import pkg_resources
from os import makedirs, path, environ, getcwd
from tempfile import mkdtemp
from shutil import rmtree


def get_dir(dir, cwd=None, permissions=None, exist_ok=None):

    permissions = 0o0775 if permissions is None else permissions
    exist_ok = True if exist_ok is None else exist_ok
    cwd = getcwd() if cwd is None else cwd

    abs_dir = get_absolute_path(dir, cwd)
    try:
        makedirs(abs_dir, mode=permissions)
    except error:
        if not exist_ok:
            raise
    return abs_dir    


def get_absolute_path(p, cwd=None):
    """
    Get absolute path relative to cwd or current working directory
    """

    cwd = getcwd() if cwd is None else cwd

    return p if path.isabs(p) else path.normpath(path.join(cwd, p))


def get_version():
    """
    Returns current version of the package if it's installed
    """

    pkg = pkg_resources.require("cwl_airflow")
    return pkg[0].version if pkg else "unknown version"


class CleanAirflowImport():
    """
    Replaces AIRFLOW_HOME and AIRFLOW_CONFIG from os.environ
    with temporary values. On exit either restores the previous values
    or removes them from os.environ, and cleans temp directory.
    Useful when importing modules from Airflow, that silently create
    airflow folder. Note, all the changes are made only within Python.
    """


    def __enter__(self):
        self.backup_airflow_home = environ.get("AIRFLOW_HOME")
        self.backup_airflow_config = environ.get("AIRFLOW_CONFIG")
        self.temp_airflow_home = mkdtemp()
        environ["AIRFLOW_HOME"] = self.temp_airflow_home
        environ["AIRFLOW_CONFIG"] = path.join(self.temp_airflow_home, "airflow.cfg")


    def __exit__(self, type, value, traceback):
        rmtree(self.temp_airflow_home)

        if self.backup_airflow_home is not None:
            environ["AIRFLOW_HOME"] = self.backup_airflow_home
        else:
            del environ["AIRFLOW_HOME"]

        if self.backup_airflow_config is not None:
            environ["AIRFLOW_CONFIG"] = self.backup_airflow_config
        else:
            del environ["AIRFLOW_CONFIG"]