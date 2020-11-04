import sys
import os
import re
import uuid
import shutil
import logging

from subprocess import run, DEVNULL, CalledProcessError

from cwl_airflow.utilities.helpers import (
    get_dir,
    CleanAirflowImport
)

with CleanAirflowImport():
    from airflow import models
    from airflow.configuration import conf
    from airflow.utils.db import merge_conn
    from airflow.utils.dag_processing import list_py_file_paths
    from cwl_airflow.utilities.cwl import overwrite_deprecated_dag


def run_init_config(args):
    """
    Runs sequence of steps required to configure CWL-Airflow
    for the first time. Safe to run several times
    """

    init_airflow_db(args)
    patch_airflow_config(args.config)
    # add_connections(args)
    if args.upgrade:
        upgrade_dags(args.config)
    copy_dags(args.home)


def init_airflow_db(args):
    """
    Sets AIRFLOW_HOME and AIRFLOW_CONFIG from args.
    Call airflow initdb from subprocess to make sure
    that the only two things we should care about
    are AIRFLOW_HOME and AIRFLOW_CONFIG
    """

    custom_env = os.environ.copy()
    custom_env["AIRFLOW_HOME"] = args.home
    custom_env["AIRFLOW_CONFIG"] = args.config
    try:
        run(
            ["airflow", "initdb"],  # TODO: check what's the difference initdb from updatedb
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
    Updates provided Airflow configuration file to include defaults for cwl-airflow.
    If something went wrong, restores the original airflow.cfg from the backed up copy
    """

    # TODO: add cwl section with the following parameters:
    # - singularity
    # - use_container

    patches = [
        ["sed", "-i", "-e", "s/^dags_are_paused_at_creation.*/dags_are_paused_at_creation = False/g", airflow_config],
        ["sed", "-i", "-e", "s/^load_examples.*/load_examples = False/g", airflow_config],
        ["sed", "-i", "-e", "s/^logging_config_class.*/logging_config_class = cwl_airflow.config_templates.airflow_local_settings.DEFAULT_LOGGING_CONFIG/g", airflow_config],
        ["sed", "-i", "-e", "s/^hide_paused_dags_by_default.*/hide_paused_dags_by_default = True/g", airflow_config]
    ]

    airflow_config_backup = airflow_config + "_backup_" + str(uuid.uuid4())
    try:
        shutil.copyfile(airflow_config, airflow_config_backup)
        for patch in patches:
            run(
                patch,
                shell=False,  # for proper handling of filenames with spaces
                check=True,
                stdout=DEVNULL,
                stderr=DEVNULL
            )
    except (CalledProcessError, FileNotFoundError) as err:
        logging.error(f"""Failed to patch Airflow configuration file. Restoring from the backup and exiting.\n{err}""")
        if os.path.isfile(airflow_config_backup):
            shutil.copyfile(airflow_config_backup, airflow_config)
        sys.exit(1)
    finally:
        if os.path.isfile(airflow_config_backup):
            os.remove(airflow_config_backup)


def upgrade_dags(airflow_config):
    """
    Corrects old style DAG python files into the new format.
    Reads configuration from "airflow_config". Uses standard
    "conf.get" instead of "conf_get", because the fields we
    use are always set. Copies all deprecated dags into the 
    "deprecated_dags" folder, adds deprecated DAGs to the
    ".airflowignore" file created within that folder. Original
    DAG files are replaced with the new ones (with base64
    encoded zlib compressed workflow content), original workflow
    files remain unchanged.
    """

    conf.read(airflow_config)
    dags_folder = conf.get("core", "dags_folder")
    for dag_location in list_py_file_paths(                     # will skip all DAGs from ".airflowignore"
        directory=dags_folder,
        safe_mode=conf.get("core", "dag_discovery_safe_mode"),  # use what user set in his config
        include_examples=False
    ):
        overwrite_deprecated_dag(                               # upgrades only deprecated DAGs, skips others
            dag_location=dag_location,
            deprecated_dags_folder=os.path.join(
                dags_folder,
                "deprecated_dags"
            )
        )


def copy_dags(airflow_home, source_folder=None):
    """
    Copies *.py files (dags) from source_folder (default ../../extensions/dags)
    to dags_folder, which is always {airflow_home}/dags
    """

    if source_folder is None:
        source_folder = os.path.join(
            os.path.dirname(
                os.path.abspath(
                    os.path.join(__file__, "../../")     
                )
            ), 
            "extensions/dags",
        )

    target_folder = get_dir(os.path.join(airflow_home, "dags"))
    for root, dirs, files in os.walk(source_folder):
        for filename in files:
            if re.match(".*\\.py$", filename) and filename != "__init__.py":
                if not os.path.isfile(os.path.join(target_folder, filename)):
                    shutil.copy(os.path.join(root, filename), target_folder)

# not used anymore
def add_connections(args):
    """
    Sets AIRFLOW_HOME and AIRFLOW_CONFIG from args.
    Call 'airflow connections --add' from subproces to make sure that
    the only two things we should care about are AIRFLOW_HOME and
    AIRFLOW_CONFIG. Adds "process_report" connections to the Airflow DB
    that is used to report workflow execution progress and results.
    """

    custom_env = os.environ.copy()
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