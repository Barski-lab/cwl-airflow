import argparse
import pytest

from configparser import ConfigParser
from os import path, listdir
from tempfile import mkdtemp
from shutil import rmtree

from cwl_airflow.components.init.config import (
    init_airflow_db,
    patch_airflow_config,
    copy_dags
)


def test_init_airflow_db():
    temp_home = mkdtemp()    
    temp_airflow_home = path.join(temp_home, "not_default_anymore", "airflow")
    temp_airflow_cfg = path.join(temp_airflow_home, "airflow.cfg")
    
    input_args = {
        "home": temp_airflow_home,
        "config": temp_airflow_cfg
    }
    init_airflow_db(argparse.Namespace(**input_args))
    
    temp_airflow_home_content = listdir(temp_airflow_home)
    rmtree(temp_home)

    assert "airflow.db" in temp_airflow_home_content, \
        "Missing airflow.db, airflow initdb failed"


def test_patch_airflow_config():
    temp_home = mkdtemp()    
    temp_airflow_home = path.join(temp_home, "not_default_anymore", "airflow")
    temp_airflow_cfg = path.join(temp_airflow_home, "airflow.cfg")
    
    input_args = {
        "home": temp_airflow_home,
        "config": temp_airflow_cfg
    }
    init_airflow_db(argparse.Namespace(**input_args))

    patch_airflow_config(temp_airflow_cfg)
    
    conf = ConfigParser()
    conf.read(temp_airflow_cfg)

    rmtree(temp_home)

    assert not conf.getboolean("core", "dags_are_paused_at_creation") and \
           not conf.getboolean("core", "load_examples") and \
           conf.getboolean("webserver", "hide_paused_dags_by_default")


def test_copy_dags():
    temp_home = mkdtemp()    
    temp_airflow_home = path.join(temp_home, "not_default_anymore", "airflow")
    temp_airflow_dags_folder = path.join(temp_airflow_home, "dags")
    temp_airflow_cfg = path.join(temp_airflow_home, "airflow.cfg")
    
    input_args = {
        "home": temp_airflow_home,
        "config": temp_airflow_cfg
    }
    init_airflow_db(argparse.Namespace(**input_args))

    copy_dags(temp_airflow_home)
    
    temp_airflow_dags_folder_content = listdir(temp_airflow_dags_folder)
    rmtree(temp_home)

    assert "clean_dag_run.py" in temp_airflow_dags_folder_content