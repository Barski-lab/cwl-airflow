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
    """
    Runs sequence of steps required to configure CWL-Airflow
    for the first time. Safe to run several times
    """

    init_airflow_db(args)
    patch_airflow_config(args.config)
    add_connections(args)
    copy_dags(args.home)


def init_airflow_db(args):
    """
    Sets AIRFLOW_HOME and AIRFLOW_CONFIG from args.
    Call airflow initdb from subprocess to make sure
    that the only two things we should care about
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
            if re.match(".*\\.py$", filename) and filename != "__init__.py":
                if not path.isfile(path.join(target_folder, filename)):
                    shutil.copy(path.join(root, filename), target_folder)


def add_connections(args):
    """
    Sets AIRFLOW_HOME and AIRFLOW_CONFIG from args.
    Call 'airflow connections --add' from subproces to make sure that
    the only two things we should care about are AIRFLOW_HOME and
    AIRFLOW_CONFIG. Adds "process_report" connections to the Airflow DB
    that is used to report workflow execution progress and results.
    """

    custom_env = environ.copy()
    custom_env["AIRFLOW_HOME"] = args.home
    custom_env["AIRFLOW_CONFIG"] = args.config
    try:
        run(
            [
                "airflow", "connections", "--add",
                "--conn_id", "process_report",
                "--conn_type", "http",
                "--conn_host", "localhost",
                "--conn_port", "3070",
                "--conn_extra", "{\"endpoint\":\"/airflow/\"}"
            ],
            env=custom_env,
            check=True,
            stdout=DEVNULL,
            stderr=DEVNULL
        )
    except (CalledProcessError, FileNotFoundError) as err:
        logging.error(f"""Failed to run 'airflow connections --add'. Exiting.\n{err}""")
        sys.exit(1)