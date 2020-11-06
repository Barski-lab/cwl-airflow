#! /usr/bin/env python3
import json
import jwt
import logging

from airflow.models import Variable
from airflow.utils.state import State
from airflow.hooks.http_hook import HttpHook


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


def post_progress(context, from_task=None):
    from_task = False if from_task is None else from_task
    try:
        dag_run = context["dag_run"]
        len_tis = len(dag_run.get_task_instances())
        len_tis_success = len(dag_run.get_task_instances(state=State.SUCCESS)) + int(from_task)
        data = sign_with_jwt(
            {
                "state": dag_run.state,
                "dag_id": dag_run.dag_id,
                "run_id": dag_run.run_id,
                "progress": int(len_tis_success / len_tis * 100),
                "error": context["reason"] if dag_run.state == State.FAILED else ""
            }
        )
        http_hook.run(endpoint=ROUTES["progress"], json={"payload": data})
    except Exception as err:
        logging.debug(f"Failed to POST progress updates. \n {err}")


def post_results(context):
    """
    Results are collected from the task with id "CWLJobGatherer". We cannot use
    isinstance(task, CWLJobGatherer) to find the proper task because of the
    endless import loop (file where we define CWLJobGatherer class import this
    file). If CWLDAG is contsructed with custom gatherer node, posting results
    might not work. We need to except missing results file as the same callback
    is used for clean_dag_run DAG
    """
    try:
        dag_run = context["dag_run"]
        results = {}
        try:
            results_location = context["ti"].xcom_pull(task_ids="CWLJobGatherer")
            with open(results_location, "r") as input_stream:
                results = json.load(input_stream)
        except Exception as err:
            logging.debug(f"Failed to read results. \n {err}")
        data = sign_with_jwt(
            {
                "dag_id": dag_run.dag_id,
                "run_id": dag_run.run_id,
                "results": results
            }
        )
        http_hook.run(endpoint=ROUTES["results"], json={"payload": data})
    except Exception as err:
        logging.debug(f"Failed to POST results. \n {err}")


def post_status(context):
    try:
        dag_run = context["dag_run"]
        ti = context["ti"]
        data = sign_with_jwt(
            {
                "state": ti.state,
                "dag_id": dag_run.dag_id,
                "run_id": dag_run.run_id,
                "task_id": ti.task_id
            }
        )
        http_hook.run(endpoint=ROUTES["status"], json={"payload": data})
    except Exception as err:
        logging.debug(f"Failed to POST status updates. \n {err}")


def task_on_success(context):
    post_progress(context, True)
    post_status(context)


def task_on_failure(context):
    post_status(context)


def task_on_retry(context):
    post_status(context)


def dag_on_success(context):
    post_progress(context)
    post_results(context)


def dag_on_failure(context):
    post_progress(context)
