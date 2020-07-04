import sys
import argparse
import pytest
import tempfile

from configparser import ConfigParser
from os import path, listdir

from shutil import rmtree
from subprocess import run, DEVNULL, CalledProcessError

from cwl_airflow.components.init.config import (
    init_airflow_db,
    patch_airflow_config,
    add_connections,
    copy_dags
)


DATA_FOLDER = path.abspath(path.join(path.dirname(__file__), "data"))
if sys.platform == "darwin":                                           # docker has troubles of mounting /var/private on macOs
    tempfile.tempdir = "/private/tmp"


def test_init_airflow_db():
    temp_home = tempfile.mkdtemp()
    temp_airflow_home = path.join(temp_home, "not_default_anymore", "airflow")
    temp_airflow_cfg = path.join(temp_airflow_home, "airflow.cfg")
    
    input_args = {
        "home": temp_airflow_home,
        "config": temp_airflow_cfg
    }

    try:
        init_airflow_db(argparse.Namespace(**input_args))       # fails with SystemExit
        temp_airflow_home_content = listdir(temp_airflow_home)  # fails with FileNotFoundError
    except BaseException as err:
        assert False, f"Failed to run test. \n {err}"
    finally:
        rmtree(temp_home)

    assert "airflow.db" in temp_airflow_home_content, \
           "Missing airflow.db, airflow initdb failed"


def test_patch_airflow_config():
    temp_home = tempfile.mkdtemp()
    temp_airflow_home = path.join(temp_home, "not_default_anymore", "airflow")
    temp_airflow_cfg = path.join(temp_airflow_home, "airflow.cfg")
    
    input_args = {
        "home": temp_airflow_home,
        "config": temp_airflow_cfg
    }

    try:
        init_airflow_db(argparse.Namespace(**input_args))  # fails with SystemExit
        patch_airflow_config(temp_airflow_cfg)             # fails with SystemExit
        conf = ConfigParser()
        conf.read(temp_airflow_cfg)                        # never fails
    except BaseException as err:
        assert False, f"Failed to run test. \n {err}"
    finally:
        rmtree(temp_home)

    assert not conf.getboolean("core", "dags_are_paused_at_creation") and \
           not conf.getboolean("core", "load_examples") and \
           conf.getboolean("webserver", "hide_paused_dags_by_default"), \
           "Failed to update Airflow configuration file"


def test_copy_dags():
    temp_home = tempfile.mkdtemp()
    temp_airflow_home = path.join(temp_home, "not_default_anymore", "airflow")
    temp_airflow_dags_folder = path.join(temp_airflow_home, "dags")
    temp_airflow_cfg = path.join(temp_airflow_home, "airflow.cfg")
    
    input_args = {
        "home": temp_airflow_home,
        "config": temp_airflow_cfg
    }

    try:
        init_airflow_db(argparse.Namespace(**input_args))                     # fails with SystemExit
        copy_dags(temp_airflow_home)                                          # never fails
        temp_airflow_dags_folder_content = listdir(temp_airflow_dags_folder)  # fails with FileNotFoundError
    except BaseException as err:
        assert False, f"Failed to run test. \n {err}"
    finally:
        rmtree(temp_home)
    
    assert "clean_dag_run.py" in temp_airflow_dags_folder_content, \
           "Failed to find 'clean_dag_run.py' in dags folder"


def test_add_connections(monkeypatch):
    temp_home = tempfile.mkdtemp()
    temp_airflow_home = path.join(temp_home, "not_default_anymore", "airflow")
    temp_airflow_cfg = path.join(temp_airflow_home, "airflow.cfg")
    monkeypatch.setenv("AIRFLOW_HOME", temp_airflow_home)
    monkeypatch.setenv("AIRFLOW_CONFIG", temp_airflow_cfg)

    input_args = {
        "home": temp_airflow_home,
        "config": temp_airflow_cfg
    }

    # don't need to setup env, because it should be inherited
    try:
        init_airflow_db(argparse.Namespace(**input_args))  # fails with SystemExit
        add_connections(argparse.Namespace(**input_args))  # fails with SystemExit
        stdout = run(                                      # fails with CalledProcessError or FileNotFoundError
            ["airflow", "connections", "--list"],
            check=True,
            capture_output=True,
            text=True
        ).stdout
    except BaseException as err:
        assert False, f"Failed to run test. \n {err}"
    finally:
        rmtree(temp_home)

    assert "process_report" in stdout, \
           "Connection 'process_report' is missing"