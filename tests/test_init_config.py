import sys
import argparse
import pytest
import tempfile
import shutil

from configparser import ConfigParser
from os import path, listdir

from subprocess import run, DEVNULL, CalledProcessError

from cwl_airflow.components.init.config import (
    init_airflow_db,
    patch_airflow_config,
    add_connections,
    copy_dags,
    upgrade_dags
)


DATA_FOLDER = path.abspath(path.join(path.dirname(__file__), "data"))
if sys.platform == "darwin":                                           # docker has troubles of mounting /var/private on macOs
    tempfile.tempdir = "/private/tmp"


def test_upgrade_dags(monkeypatch):
    """
    Checks only if files were moved to the correct locations.
    Doesn't check if DAG was upgraded correctly, because it's
    checked in a separete "test_overwrite_deprecated_dag" test
    """

    temp_home = tempfile.mkdtemp()
    monkeypatch.delenv("AIRFLOW_HOME", raising=False)
    monkeypatch.delenv("AIRFLOW_CONFIG", raising=False)
    monkeypatch.setattr(
        path,
        "expanduser",
        lambda x: x.replace("~", temp_home)
    )

    control_dags_folder_content = [
        "bam-bedgraph-bigwig-single.cwl",
        "bam_bedgraph_bigwig_single_new_format.py",
        "bam_bedgraph_bigwig_single_old_format.py",
        "dummy_airflow_dag.py",
        "deprecated_dags"
    ]
    control_deprecated_dags_folder_content = [
        "bam_bedgraph_bigwig_single_old_format.py",
        ".airflowignore"
    ]

    airflow_home = path.join(temp_home, "not_default_anymore", "airflow")
    airflow_cfg = path.join(airflow_home, "airflow.cfg")
    dags_folder = path.join(airflow_home, "dags")

    shutil.copytree(path.join(DATA_FOLDER, "dags"), dags_folder)           # copy dags
    shutil.copy(                                                           # copy workflow
        path.join(
            DATA_FOLDER, "workflows", "bam-bedgraph-bigwig-single.cwl"
        ),
        dags_folder
    )

    input_args = {
        "home": airflow_home,
        "config": airflow_cfg
    }

    try:
        init_airflow_db(argparse.Namespace(**input_args))
        upgrade_dags(argparse.Namespace(**input_args))
        dags_folder_content = listdir(dags_folder)
        deprecated_dags_folder_content = listdir(
            path.join(dags_folder, "deprecated_dags")                      # "deprecated_dags" is harcoded in "upgrade_dags" function
        )
    except BaseException as err:
        assert False, f"Failed to run test. \n {err}"
    finally:
        shutil.rmtree(temp_home)

    assert all(
        f in dags_folder_content for f in control_dags_folder_content
    ), "Missing files in the dags folder"
    assert all(
        f in deprecated_dags_folder_content for f in control_deprecated_dags_folder_content
    ), "Missing files in the folder with deprecated dags"


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
        shutil.rmtree(temp_home)

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
        init_airflow_db(argparse.Namespace(**input_args))       # fails with SystemExit
        patch_airflow_config(argparse.Namespace(**input_args))  # fails with SystemExit
        conf = ConfigParser()
        conf.read(temp_airflow_cfg)                             # never fails
    except BaseException as err:
        assert False, f"Failed to run test. \n {err}"
    finally:
        shutil.rmtree(temp_home)

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
        copy_dags(argparse.Namespace(**input_args))                           # never fails
        temp_airflow_dags_folder_content = listdir(temp_airflow_dags_folder)  # fails with FileNotFoundError
    except BaseException as err:
        assert False, f"Failed to run test. \n {err}"
    finally:
        shutil.rmtree(temp_home)
    
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
        shutil.rmtree(temp_home)

    assert "process_report" in stdout, \
           "Connection 'process_report' is missing"