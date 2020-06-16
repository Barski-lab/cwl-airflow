import sys
import re
import configparser
import shutil
import logging

from os import environ, path, walk
from plistlib import load, dump
from subprocess import run, DEVNULL, CalledProcessError

from cwl_airflow.utilities.helpers import (
    get_dir,
    CleanAirflowImport
)

with CleanAirflowImport():
    from airflow import models
    from airflow.utils.db import merge_conn
    

def run_init_config(args):
    init_airflow_db(args)
    patch_airflow_config(args.config)
    copy_dags(args.home)
    # add_connections()


def init_airflow_db(args):
    """
    Sets AIRFLOW_HOME and AIRFLOW_CONFIG from args.
    Although, both env variables should have been already set
    by argument parser, we set them again mostly because of
    the tests. For now call airflow initdb from subprocess to
    make sure that the only two things we should care about
    are AIRFLOW_HOME and AIRFLOW_CONFIG
    """
    custom_env = environ.copy()
    custom_env["AIRFLOW_HOME"] = args.home
    custom_env["AIRFLOW_CONFIG"] = args.config
    try:
        run(
            ["airflow", "initdb"],
            env=custom_env,
            check=True,
            stdout=DEVNULL,
            stderr=DEVNULL
        )
    except (CalledProcessError, FileNotFoundError) as err:
        logging.error(f"""Failed to run 'airflow initdb'. Exiting.\n{err}""")
        sys.exit(1)


def patch_airflow_config(airflow_config):
    """
    Updates provided Airflow configuration file to include defaults for cwl-airflow
    """

    patch = f"""
    sed -i -e 's/^dags_are_paused_at_creation.*/dags_are_paused_at_creation = False/g' {airflow_config} && \
    sed -i -e 's/^load_examples.*/load_examples = False/g' {airflow_config} && \
    sed -i -e 's/^hide_paused_dags_by_default.*/hide_paused_dags_by_default = True/g' {airflow_config}
    """
    try:
        run(
            patch,
            shell=True,
            check=True,
            stdout=DEVNULL,
            stderr=DEVNULL
        )
    except (CalledProcessError, FileNotFoundError) as err:
        logging.error(f"""Failed to patch Airflow configuration file. Exiting.\n{err}""")
        sys.exit(1)


def copy_dags(airflow_home, source_folder=None):
    """
    Copies *.py files (dags) from source_folder (default ../../extensions/dags)
    to dags_folder, which is always {airflow_home}/dags
    """

    if source_folder is None:
        source_folder = path.join(
            path.dirname(
                path.abspath(
                    path.join(__file__, "../../")     
                )
            ), 
            "extensions/dags",
        )

    target_folder = get_dir(path.join(airflow_home, "dags"))
    for root, dirs, files in walk(source_folder):
        for filename in files:
            if re.match(".*\.py$", filename) and filename != "__init__.py":
                if not path.isfile(path.join(target_folder, filename)):
                    shutil.copy(path.join(root, filename), target_folder)


def add_connections():
    merge_conn(models.Connection(conn_id = "process_report",
        conn_type = "http",
        host = "localhost",
        port = "3070",
        extra = "{\"endpoint\":\"/airflow/\"}")
    )