#! /usr/bin/env python3
import json
import jwt
import logging

from airflow.models import Variable
from airflow.utils.state import State
from airflow.hooks.http_hook import HttpHook
from airflow.configuration import conf
from airflow.exceptions import AirflowNotFoundException

from cwl_airflow.utilities.cwl import (
    get_workflow_execution_stats,
    get_default_cwl_args,
    remove_dag_run_tmp_data
)


CONN_ID = "process_report"
ROUTES = {
    "progress": "airflow/progress",
    "results":  "airflow/results",
    "status":   "airflow/status"
}
PRIVATE_KEY = "process_report_private_key"
ALGORITHM = "process_report_algorithm"

http_hook = HttpHook(method="POST", http_conn_id=CONN_ID)  # won't fail even if CONN_ID doesn't exist


def sign_with_jwt(data):
    try:
        data = jwt.encode(
            payload=data,
            key=Variable.get(PRIVATE_KEY),
            algorithm=Variable.get(ALGORITHM)
        ).decode("utf-8")
    except Exception as err:
        logging.debug(f"Failed to sign data with JWT key. \n {err}")
    return data


def get_error_category(context):
    """
    This function should be called only from the dag_run failure callback.
    It's higly relies on the log files, so logging level in airflow.cfg
    shouldn't be lower than ERROR. We load log file only for the latest task
    retry, because the get_error_category function is called when the dag_run
    has failed, so all previous task retries didn't bring any positive results.
    We load logs only for the actually failed task, not for upstream_failed
    tasks. All error categories are sorted by priority from higher level to the
    lower one. We report only one (the highest, the first found) error category
    per failed task. Error categories from all failed tasks are combined and
    deduplicated. The "Failed to run workflow step" category additionally is
    filled with failed task ids. The returned value is always a string.
    """

    ERROR_MARKERS = {
        "docker: Error response from daemon":                 "Docker problems. Contact support team",
        "Docker is not available for this tool":              "Docker or Network problems. Contact support team",
        "You have reached your pull rate limit":              "Docker pull limit reached. Restart in 6 hours",
        "ERROR - Received SIGTERM. Terminating subprocesses": "Workflow was stopped. Restart with the lower threads or memory parameters",
        "Failed to run workflow step":                        "Workflow step(s) {} failed. Contact support team"
    }

    # docker daemon is not running; networks is unavailable to pull the docker image or it doesn't exist
    # something took too much resources and Aiflow killed the process or something externally has stopped the task
    # cwltool exited with error when executing workflow step

    dag_run = context["dag_run"]
    failed_tis = dag_run.get_task_instances(state=State.FAILED)
    log_handler = next(                                              # to get access to logs
        (
            h for h in logging.getLogger("airflow.task").handlers
            if h.name == conf.get("logging", "task_log_reader")      # starting from Airflow 2.0.0 moved from [core] to [logging] section
        ),
        None
    )

    categories = set()                                               # use set to prevent duplicates

    for ti in failed_tis:
        ti.task = context["dag"].get_task(ti.task_id)                # for some reasons when retreived from DagRun we need to set "task" property from the DAG
        try:                                                         # in case log files were deleted or unavailable
            logs, _ = log_handler.read(ti)                           # logs is always a list.
            for marker, category in ERROR_MARKERS.items():
                if marker in logs[-1]:                               # logs[-1] is a string with \n from the last task retry
                    categories.add(category)
                    break
        except Exception as err:
            logging.debug(f"Failed to define the error category for task {ti.task_id}. \n {err}")

    if categories:
        return ". ".join(categories).format(", ".join( [ti.task_id for ti in failed_tis] ))  # mainly to fill in the placeholder with failed task ids
    return "Unknown error. Contact support team"


def post_progress(context, from_task=None):
    """
    If dag_run failed but this function was run from the task callback,
    error would be always "". The "error" is not "" only when this function
    will be called from the DAG callback, thus making it the last and the only
    message with the meaningful error description. If function was called not
    from a task and we failed to send a request we need to guarantee that message
    is not getting lost so we back it up into the Variable to be able to resend
    it later. We don't backup not sent messages if user didn't add the required
    connection in Airflow.
    """

    from_task = False if from_task is None else from_task

    dag_run = context["dag_run"]
    len_tis = len(dag_run.get_task_instances())
    len_tis_success = len(dag_run.get_task_instances(state=State.SUCCESS)) + int(from_task)
    progress = 100 if len_tis == 0 else int(len_tis_success / len_tis * 100)
    message = {
        "payload": sign_with_jwt(
            {
                "state": dag_run.state,
                "dag_id": dag_run.dag_id,
                "run_id": dag_run.run_id,
                "progress": progress,
                "statistics": get_workflow_execution_stats(context) if not from_task else "",
                "error": get_error_category(context) if dag_run.state == State.FAILED and not from_task else ""
            }
        )
    }
    try:
        http_hook.run(endpoint=ROUTES["progress"], json=message, extra_options={"timeout": 30})
    except AirflowNotFoundException as err:
        logging.debug(f"Failed to POST progress updates. Skipping \n {err}")
    except Exception as err:
        logging.debug(f"Failed to POST progress updates. \n {err}")
        if not from_task and progress != 100:                        # we don't need to resend messages with progress == 100
            logging.debug("Save the message into the Variables")
            Variable.set(
                key=f"post_progress__{dag_run.dag_id}__{dag_run.run_id}",
                value={
                    "message": message,
                    "endpoint": ROUTES["progress"]
                },
                serialize_json=True
            )


def post_results(context):
    """
    Results are collected from the task with id "CWLJobGatherer". We cannot use
    isinstance(task, CWLJobGatherer) to find the proper task because of the
    endless import loop (file where we define CWLJobGatherer class import this
    file). If CWLDAG is contsructed with custom gatherer node, posting results
    might not work. We need to except missing results file as the same callback
    is used for clean_dag_run DAG. If we failed to send a request we need to
    guarantee that message is not getting lost so we back it up into the Variable
    to be able to resend it later. We don't backup not sent messages if user didn't
    add the required connection in Airflow.
    """

    dag_run = context["dag_run"]
    results = {}
    try:
        results_location = context["ti"].xcom_pull(task_ids="CWLJobGatherer")
        with open(results_location, "r") as input_stream:
            results = json.load(input_stream)
    except Exception as err:
        logging.debug(f"Failed to read results. \n {err}")
    message = {
        "payload": sign_with_jwt(
            {
                "dag_id": dag_run.dag_id,
                "run_id": dag_run.run_id,
                "results": results
            }
        )
    }
    try:
        http_hook.run(endpoint=ROUTES["results"], json=message, extra_options={"timeout": 30})
    except AirflowNotFoundException as err:
        logging.debug(f"Failed to POST results. Skipping \n {err}")
    except Exception as err:
        logging.debug(f"Failed to POST results. Save the message into the Variables \n {err}")
        Variable.set(
            key=f"post_results__{dag_run.dag_id}__{dag_run.run_id}",
            value={
                "message": message,
                "endpoint": ROUTES["results"]
            },
            serialize_json=True
        )


def post_status(context):
    dag_run = context["dag_run"]
    ti = context["ti"]
    message = {
        "payload": sign_with_jwt(
            {
                "state": ti.state,
                "dag_id": dag_run.dag_id,
                "run_id": dag_run.run_id,
                "task_id": ti.task_id
            }
        )
    }
    try:
        http_hook.run(endpoint=ROUTES["status"], json=message, extra_options={"timeout": 30})
    except Exception as err:
        logging.debug(f"Failed to POST status updates. \n {err}")


def clean_up(context):
    """
    Loads "cwl" arguments from the DAG, just in case updates them with
    all required defaults, and, unless "keep_tmp_data" was set to True,
    tries to remove all remporary data and related records in the XCom
    table. If this function is called from clean_dag_run or any other
    DAG that doesn't have "cwl" in the "default_args" we will catch
    KeyError exception
    """
    try:
        default_cwl_args = get_default_cwl_args(
            context["dag"].default_args["cwl"]
        )
        if not default_cwl_args["keep_tmp_data"]:
            dag_run = context["dag_run"]
            remove_dag_run_tmp_data(dag_run)          # safe to run as it has its own exception handling
            for ti in dag_run.get_task_instances():
                ti.clear_xcom_data()
    except KeyError as err:                           # will catch if called from clean_dag_run
        logging.info(f"Failed to clean up data for current DAG, due to \n {err}")


def task_on_success(context):
    post_progress(context, True)
    post_status(context)


def task_on_failure(context):
    # no need to post progress as it hasn't been changed
    post_status(context)


def task_on_retry(context):
    # no need to post progress as it hasn't been changed
    post_status(context)


def dag_on_success(context):
    post_progress(context)
    post_results(context)
    clean_up(context)


def dag_on_failure(context):
    # we need to post progress, because we will also report error in it
    post_progress(context)
    clean_up(context)