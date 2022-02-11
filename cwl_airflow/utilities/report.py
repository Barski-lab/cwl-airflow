#! /usr/bin/env python3
import os
import json
import logging

from airflow.models import Variable
from airflow.utils.state import State
from airflow.hooks.http_hook import HttpHook
from airflow.utils.session import create_session
from airflow.configuration import conf
from airflow.exceptions import AirflowNotFoundException

from cwl_airflow.utilities.cwl import (
    get_workflow_execution_stats,
    get_default_cwl_args,
    remove_dag_run_tmp_data
)
from cwl_airflow.utilities.loggers import (
    get_log_handler,
    get_log_location
)

CONN_ID = "process_report"
ROUTES = {
    "progress": "airflow/progress",
    "results":  "airflow/results",
    "status":   "airflow/status"
}


http_hook = HttpHook(method="POST", http_conn_id=CONN_ID)  # won't fail even if CONN_ID doesn't exist


def resend_reports():
    with create_session() as session:
        for var in session.query(Variable):
            if any(prefix in var.key for prefix in ["post_progress__", "post_results__"]):
                logging.debug(f"Retreive {var.key} from Variables")
                value = Variable.get(key=var.key, deserialize_json=True)
                try:
                    http_hook.run(
                        endpoint=value["endpoint"],
                        json=value["message"],
                        extra_options={"timeout": 30}  # need to have timeout otherwise may get stuck forever
                    )
                    Variable.delete(key=var.key)
                    logging.debug(f"Value from {var.key} variable has been successfully sent")
                except Exception as err:
                    logging.debug(f"Failed to POST value from {var.key} variable. Will retry in the next run \n {err}")


def append_cwl_log(context):
    """
    Appends the latest CWL log to the end of the Airflow log.
    """

    ti = context["ti"]
    cwl_log_handler = get_log_handler("cwltool", "cwltool")
    cwl_logs, _ = cwl_log_handler.read(ti)
    latest_cwl_log_content = cwl_logs[-1][0][1]                          # [-1] - to get only the last task retry, [0] - there is only one item in array. [1] - to get the actual log content as a string
    ti.log.info("CWL LOGS")
    ti.log.info(latest_cwl_log_content)


def get_error_info(context):
    """
    This function should be called only from the dag_run failure callback.
    It's higly relies on the log files, so logging level in airflow.cfg
    shouldn't be lower than ERROR. We search and load log files only for the
    latest task retry attempt, because the get_error_category function is called
    when the dag_run has failed, so all previous task retries didn't bring any
    positive results.
    We load airflow logs only for the actually failed task, not for upstream_failed
    tasks. All error categories are sorted by priority from higher level to the
    lower one. We report only one (the highest, the first found) error category
    per failed task. Error categories from all failed tasks are combined and
    deduplicated. The "Failed to run workflow step" category additionally is
    filled with failed task ids.
    Additionally we return file location for airflow and cwl logs. If any of them
    is not present, it won't be added to the returned object.
    The returned value is an object with fields "label" to describe to error category,
    and logs - another object with logs collected for all failed steps and previos
    (related upstreams) steps.
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
    success_tis = dag_run.get_task_instances(state=State.SUCCESS)

    airflow_handler = get_log_handler("airflow.task", conf.get("logging", "task_log_reader"))
    cwl_handler = get_log_handler("cwltool", "cwltool")

    categories = set()                                               # use set to prevent duplicates

    for ti in failed_tis:
        ti.task = context["dag"].get_task(ti.task_id)                # for some reasons when retreived from DagRun we need to set "task" property from the DAG
        try:                                                         # in case log files were deleted or unavailable
            logs, _ = airflow_handler.read(ti)                       # logs is always a list, so we need to take [0]
            for marker, category in ERROR_MARKERS.items():
                if marker in logs[-1][0][1]:                         # [-1] - to get only the last task retry, [0] - there is only one item in array. [1] - to get the actual log content as a string
                    categories.add(category)
                    break
        except Exception as err:
            logging.debug(f"Failed to define the error category for task {ti.task_id}. \n {err}")

    upstream_tis = []
    for ti in success_tis:
        ti.task = context["dag"].get_task(ti.task_id)
        if (set(ti.task.downstream_task_ids) & set([ti.task_id for ti in failed_tis])):
            upstream_tis.append(ti)                                                       # this upstream task could cause the failure of one of the tasks from failed_tis

    collected_logs = {
        "failed_steps": {},
        "previous_steps": {}
    }
    for ti in failed_tis + upstream_tis:
        current_log = {}
        try:
            current_log["airflow"] = get_log_location(airflow_handler, ti)
        except Exception as err:
            logging.debug(f"Failed to find the latest airflow log for {ti.task_id}. \n {err}")
        try:
            current_log["cwl"] = get_log_location(cwl_handler, ti)
        except Exception as err:
            logging.debug(f"Failed to find the latest cwl log for {ti.task_id}. \n {err}")
        if ti.task_id in [ti.task_id for ti in failed_tis]:
            collected_logs["failed_steps"][ti.task_id] = current_log
        else:
            collected_logs["previous_steps"][ti.task_id] = current_log

    label = ". ".join(categories).format(", ".join( [ti.task_id for ti in failed_tis] )) if categories else "Unknown error. Contact support team"

    return {"label": label, "logs": collected_logs}


def report_progress(context, from_task=None):
    """
    If dag_run failed but this function was run from the task callback,
    error and logs fields would be always "". The "error" and logs are
    not "" only when this function is called from the failed DAG callback,
    thus making it the last and the only message with the meaningful error
    description. Workflow execution statistics is generated only when this
    function is called from DAG (not task). Also, not delivered messages
    will be backed up only if this function was called from DAG.
    """

    from_task = False if from_task is None else from_task

    dag_run = context["dag_run"]
    len_tis = len(dag_run.get_task_instances())
    len_tis_success = len(dag_run.get_task_instances(state=State.SUCCESS)) + int(from_task)
    progress = 100 if len_tis == 0 else int(len_tis_success / len_tis * 100)
    error_info = get_error_info(context) if dag_run.state == State.FAILED and not from_task else None
    message = {
        "payload": {
            "state": dag_run.state,
            "dag_id": dag_run.dag_id,
            "run_id": dag_run.run_id,
            "progress": progress,
            "statistics": get_workflow_execution_stats(context) if not from_task else "",
            "error": error_info["label"] if error_info is not None else "",
            "logs": error_info["logs"] if error_info is not None else ""
        }
    }
    post_progress(message, not from_task)  # no need to backup progress messages that came from tasks


def report_results(context):
    """
    Results are collected from the task with id "CWLJobGatherer". We cannot use
    isinstance(task, CWLJobGatherer) to find the proper task because of the
    endless import loop (file where we define CWLJobGatherer class import this
    file). If CWLDAG is contsructed with custom gatherer node, posting results
    might not work. We need to except missing results file as the same callback
    is used for clean_dag_run DAG. All not delivered messages will be backed up.
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
        "payload": {
            "dag_id": dag_run.dag_id,
            "run_id": dag_run.run_id,
            "results": results
        }
    }
    post_results(message)


def report_status(context):
    """
    Reports status of the current task. No message backup needed.
    """

    dag_run = context["dag_run"]
    ti = context["ti"]
    message = {
        "payload": {
            "state": ti.state,
            "dag_id": dag_run.dag_id,
            "run_id": dag_run.run_id,
            "task_id": ti.task_id
        }
    }
    post_status(message)


def post_progress(message, backup=None):
    """
    If we failed to post progress report when backup was true (by default it's
    always true) we need to guarantee that message is not getting lost so we
    back it up into the Variable to be able to resend it later. We don't backup
    not sent messages if user didn't add the required connection in Airflow by
    catching AirflowNotFoundException. Function may fail only when message is not
    properly formatted.
    """

    backup = True if backup is None else backup

    try:
        http_hook.run(endpoint=ROUTES["progress"], json=message, extra_options={"timeout": 30})
    except AirflowNotFoundException as err:
        logging.debug(f"Failed to POST progress updates. Skipping \n {err}")
    except Exception as err:
        logging.debug(f"Failed to POST progress updates. \n {err}")
        if backup:
            logging.debug("Save the message into the Variables")
            Variable.set(
                key=f"post_progress__{message['payload']['dag_id']}__{message['payload']['run_id']}",
                value={
                    "message": message,
                    "endpoint": ROUTES["progress"]
                },
                serialize_json=True
            )


def post_results(message, backup=None):
    """
    If we failed to post results when backup was true (by default it's always true)
    we need to guarantee that message is not getting lost so we back it up into the
    Variable to be able to resend it later. We don't backup not sent messages if user
    didn't add the required connection in Airflow by catching AirflowNotFoundException.
    May fail only when message is not properly formatted.
    """

    backup = True if backup is None else backup

    try:
        http_hook.run(endpoint=ROUTES["results"], json=message, extra_options={"timeout": 30})
    except AirflowNotFoundException as err:
        logging.debug(f"Failed to POST results. Skipping \n {err}")
    except Exception as err:
        logging.debug(f"Failed to POST results. \n {err}")
        if backup:
            logging.debug("Save the message into the Variables")
            Variable.set(
                key=f"post_results__{message['payload']['dag_id']}__{message['payload']['run_id']}",
                value={
                    "message": message,
                    "endpoint": ROUTES["results"]
                },
                serialize_json=True
            )


def post_status(message):
    """
    We don't need to backup not delivered status updates
    so we don't save them in to Variables. Never fails.
    """

    try:
        http_hook.run(endpoint=ROUTES["status"], json=message, extra_options={"timeout": 30})
    except Exception as err:
        logging.debug(f"Failed to POST status updates. \n {err}")


def has_failed_tasks(dag_run):
    return dag_run.get_task_instances(state=State.FAILED).exists()


def clean_up(context):
    """
    Loads "cwl" arguments from the DAG, just in case updates them with
    all required defaults, and, unless "keep_tmp_data" was set to True,
    tries to remove all remporary data and related records in the XCom
    table. If this function is called from the callback of clean_dag_run
    or any other DAG that doesn't have "cwl" in the "default_args" we will
    catch KeyError exception.
    """

    try:
        default_cwl_args = get_default_cwl_args(
            context["dag"].default_args["cwl"]
        )
        dag_run = context["dag_run"]
        keep_tmp_data = default_cwl_args["keep_tmp_data"]
        if keep_tmp_data is None:
            keep_tmp_data = has_failed_tasks(dag_run)

        if not keep_tmp_data:
            remove_dag_run_tmp_data(dag_run)          # safe to run as it has its own exception handling
            for ti in dag_run.get_task_instances():
                ti.clear_xcom_data()

    except KeyError as err:                           # will catch if called from clean_dag_run
        logging.info(f"Failed to clean up data for current DAG, due to \n {err}")


def task_on_success(context):
    report_progress(context, True)
    report_status(context)
    append_cwl_log(context)


def task_on_failure(context):
    # no need to report progress as it hasn't been changed
    report_status(context)
    append_cwl_log(context)


def task_on_retry(context):
    # no need to report progress as it hasn't been changed
    report_status(context)


def dag_on_success(context):
    report_progress(context)
    report_results(context)
    clean_up(context)


def dag_on_failure(context):
    # we need to report progress, because we will also report
    # error and execution statistics in it
    report_progress(context)
    clean_up(context)