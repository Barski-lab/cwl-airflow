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
    from airflow.configuration import conf
    from airflow.exceptions import AirflowConfigException
    from airflow.utils.file import list_py_file_paths
    from cwl_airflow.utilities.cwl import overwrite_deprecated_dag


def run_init_config(args):
    """
    Runs sequence of steps required to configure CWL-Airflow
    for the first time. Safe to run several times. Upgrades
    config to correspond to Airflow 2.0.0
    """

    create_airflow_config(args)          # will create default airflow.cfg if it wasn't present
    patch_airflow_config(args)
    init_airflow_db(args)

    if args.upgrade:
        upgrade_dags(args)
    copy_dags(args)


def create_airflow_config(args):
    """
    Runs airflow --help command with AIRFLOW_HOME and AIRFLOW_CONFIG
    environment variables just to create airflow.cfg file
    """

    custom_env = os.environ.copy()
    custom_env["AIRFLOW_HOME"] = args.home
    custom_env["AIRFLOW_CONFIG"] = args.config
    try:
        run(
            ["airflow", "--help"],
            env=custom_env,
            check=True,
            stdout=DEVNULL,
            stderr=DEVNULL
        )
    except (FileNotFoundError, CalledProcessError) as err:
        logging.error(f"""Failed to find or to run airflow executable'. Exiting.\n{err}""")
        sys.exit(1)


def init_airflow_db(args):
    """
    Sets AIRFLOW_HOME and AIRFLOW_CONFIG from args.
    Call airflow db init from subprocess to make sure
    that the only two things we should care about
    are AIRFLOW_HOME and AIRFLOW_CONFIG
    """

    custom_env = os.environ.copy()
    custom_env["AIRFLOW_HOME"] = args.home
    custom_env["AIRFLOW_CONFIG"] = args.config
    try:
        run(
            ["airflow", "db", "init"],  # `db init` always runs `db upgrade` internally, so it's ok to run only `db init`
            env=custom_env,
            check=True,
            stdout=DEVNULL,
            stderr=DEVNULL
        )
    except (FileNotFoundError) as err:
        logging.error(f"""Failed to find airflow executable'. Exiting.\n{err}""")
        sys.exit(1)
    except (CalledProcessError) as err:
        logging.error(f"""Failed to run 'airflow db init'. Delete airflow.db if SQLite was used. Exiting.\n{err}""")
        sys.exit(1)


def patch_airflow_config(args):
    """
    Updates current Airflow configuration file to include defaults for cwl-airflow.
    If something went wrong, restores the original airflow.cfg from the backed up copy.
    If update to Airflow 2.0.0 is required, generates new airflow.cfg with some of the
    important parameters copied from the old airflow.cfg. Backed up copy is not deleted in
    this case.
    """

    # TODO: add cwl section with the following parameters:
    # - singularity
    # - use_container

    # CWL-Airflow specific settings
    patches = [
        ["sed", "-i", "-e", "s#^dags_are_paused_at_creation.*#dags_are_paused_at_creation = False#g", args.config],
        ["sed", "-i", "-e", "s#^load_examples.*#load_examples = False#g", args.config],
        ["sed", "-i", "-e", "s#^load_default_connections.*#load_default_connections = False#g", args.config],
        ["sed", "-i", "-e", "s#^logging_config_class.*#logging_config_class = cwl_airflow.config_templates.airflow_local_settings.DEFAULT_LOGGING_CONFIG#g", args.config],
        ["sed", "-i", "-e", "s#^hide_paused_dags_by_default.*#hide_paused_dags_by_default = True#g", args.config]
    ]

    # Minimum amount of setting that should be enough for starting
    # SequentialExecutor, LocalExecutor or CeleryExecutor with
    # the same dags and metadata database after updating to Airflow 2.0.0.
    # All other user specific settings should be manually updated from the
    # backuped airflow.cfg as a lot of them have been refactored.
    transferable_settings = [
        ("core", "dags_folder"),
        ("core", "default_timezone"),
        ("core", "executor"),
        ("core", "sql_alchemy_conn"),
        ("core", "sql_engine_encoding"),   # just in case
        ("core", "fernet_key"),            # to be able to read from the old database
        ("celery", "broker_url"),
        ("celery", "result_backend")
    ]

    # create a temporary backup of airflow.cfg to restore from if we failed to apply patches
    # this backup will be deleted after all patches applied if it wasn't created right before
    # Airflow version update to 2.0.0
    airflow_config_backup = args.config + "_backup_" + str(uuid.uuid4())
    try:
        # reading aiflow.cfg before applying any patches and creating backup
        conf.read(args.config)
        shutil.copyfile(args.config, airflow_config_backup)

        # check if we need to make airflow.cfg correspond to the Airflow 2.0.0
        # we search for [logging] section as it's present only Airflow >= 2.0.0
        airflow_version_update = not conf.has_section("logging")
        if airflow_version_update:
            logging.info("Airflow config will be upgraded to correspond to Airflow 2.0.0")
            for section, key in transferable_settings:
                try:
                    patches.append(
                        ["sed", "-i", "-e", f"s#^{key}.*#{key} = {conf.get(section, key)}#g", args.config]
                    )
                except AirflowConfigException:  # just skip missing in the config section/key
                    pass
            os.remove(args.config)              # remove old config
            create_airflow_config(args)         # create new airflow.cfg with the default values

        # Apply all patches
        for patch in patches:
            logging.debug(f"Applying patch {patch}")
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
            shutil.copyfile(airflow_config_backup, args.config)
        sys.exit(1)
    finally:
        if os.path.isfile(airflow_config_backup) and not airflow_version_update:
            os.remove(airflow_config_backup)


def upgrade_dags(args):
    """
    Corrects old style DAG python files into the new format.
    Reads configuration from "args.config". Uses standard
    "conf.get" instead of "conf_get", because the fields we
    use are always set. Copies all deprecated dags into the 
    "deprecated_dags" folder, adds deprecated DAGs to the
    ".airflowignore" file created within that folder. Original
    DAG files are replaced with the new ones (with base64
    encoded gzip compressed workflow content), original workflow
    files remain unchanged.
    """

    conf.read(args.config)                                      # this will read already patched airflow.cfg
    dags_folder = conf.get("core", "dags_folder")
    for dag_location in list_py_file_paths(                     # will skip all DAGs from ".airflowignore"
        directory=dags_folder,
        safe_mode=conf.getboolean("core", "dag_discovery_safe_mode"),  # use what user set in his config
        include_examples=False
    ):
        overwrite_deprecated_dag(                               # upgrades only deprecated DAGs, skips others
            dag_location=dag_location,
            deprecated_dags_folder=os.path.join(
                dags_folder,
                "deprecated_dags"
            )
        )


def copy_dags(args, source_folder=None):
    """
    Copies *.py files (dags) from source_folder (default ../../extensions/dags)
    to dags_folder, which is always {args.home}/dags. Overwrites existent
    files
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

    target_folder = get_dir(os.path.join(args.home, "dags"))
    for root, dirs, files in os.walk(source_folder):
        for filename in files:
            if re.match(".*\\.py$", filename) and filename != "__init__.py":
                # if not os.path.isfile(os.path.join(target_folder, filename)):
                shutil.copy(os.path.join(root, filename), target_folder)
