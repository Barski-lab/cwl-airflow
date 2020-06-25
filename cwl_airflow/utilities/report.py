#! /usr/bin/env python3
import json
import jwt
import logging
import requests

from airflow.models import Variable
from airflow.utils.state import State
from airflow.hooks.http_hook import HttpHook


CONN_ID = "process_report"
ROUTES = {
    "progress": "progress",
    "results":  "results",
    "status":   "status"
}
PRIVATE_KEY = "process_report_private_key"
ALGORITHM = "process_report_algorithm"


def prepare_connection(conn_id, route):
    http_hook = HttpHook(http_conn_id=conn_id)
    session = http_hook.get_conn()
    url = "/".join(
        [
            u.strip("/") for u in [http_hook.base_url, session.headers["endpoint"], route]
        ]
    )
    return http_hook, session, url


def sign_with_jwt(data, private_key=None, algorithm=None):
    try:
        data = jwt.encode(
            payload=data,
            key=private_key or Variable.get(PRIVATE_KEY),
            algorithm=algorithm or Variable.get(ALGORITHM)
        ).decode("utf-8")
    except Exception as err:
        logging.debug(f"Failed to sign data with JWT key. \n {err}")
    return data


def post_progress(context, from_task=None):
    from_task = False if from_task is None else from_task
    try:
        http_hook, session, url = prepare_connection(CONN_ID, ROUTES["progress"])
        dag_run = context["dag_run"]
        len_tis = len(dag_run.get_task_instances())
        len_tis_success = len(dag_run.get_task_instances(state=State.SUCCESS)) + int(from_task)
        data = sign_with_jwt(
            data={
                "state":    dag_run.state,
                "dag_id":   dag_run.dag_id,
                "run_id":   dag_run.run_id,
                "progress": int(len_tis_success / len_tis * 100),
                "error":    context["reason"] if dag_run.state == State.FAILED else ""
            }
        )
        prepped_request = session.prepare_request(
            requests.Request(
                "POST",
                url,
                json={"payload": data}
            )
        )
        http_hook.run_and_check(session, prepped_request, {})
    except Exception as err:
        logging.debug(f"Failed to POST progress updates. \n {err}")


def post_results(context):
    """
    Results are collected from the task with id "CWLJobGatherer". We cannot use
    isinstance(task, CWLJobGatherer) to find the proper task because of the
    endless import loop (file where we define CWLJobGatherer class import this
    file). If CWLDAG is contsructed with custom gatherer node, posting results
    might not work.
    """
    
    try:
        http_hook, session, url = prepare_connection(CONN_ID, ROUTES["results"])
        dag_run = context["dag_run"]
        results = ""
        try:
            results_location = context["ti"].xcom_pull(task_ids="CWLJobGatherer")
            with open(results_location, "r") as input_stream:
                results = json.load(input_stream)
        except Exception as err:
            logging.debug(f"Failed to read results. \n {err}")

        data = sign_with_jwt(
            data={
                "dag_id":  dag_run.dag_id,
                "run_id":  dag_run.run_id,
                "results": results
            }
        )
        prepped_request = session.prepare_request(
            requests.Request(
                "POST",
                url,
                json={"payload": data}
            )
        )
        http_hook.run_and_check(session, prepped_request, {})
    except Exception as err:
        logging.debug(f"Failed to POST results. \n {err}")


def post_status(context):
    try:
        http_hook, session, url = prepare_connection(CONN_ID, ROUTES["status"])
        dag_run = context["dag_run"]
        ti = context["ti"]
        data = sign_with_jwt(
            data={
                "state":    ti.state,
                "dag_id":   dag_run.dag_id,
                "run_id":   dag_run.run_id,
                "task_id":  ti.task_id
            }
        )
        prepped_request = session.prepare_request(
            requests.Request(
                "POST",
                url,
                json={"payload": data}
            )
        )
        http_hook.run_and_check(session, prepped_request, {})
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
