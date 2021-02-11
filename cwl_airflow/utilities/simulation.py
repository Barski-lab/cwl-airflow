#! /usr/bin/env python3
import threading
import logging

from time import sleep

from airflow.utils.timezone import (
    utcnow,
    parse as parsedate
)
from airflow.utils.state import State

from cwl_airflow.utilities.report import (
    post_progress,
    post_results,
    post_status
)


REPORT_CATEGORIES = {
    "progress": post_progress,
    "results": post_results,
    "status": post_status
}


def send_reports(suite_data, dag_id, run_id, delay=None):

    delay = 3 if delay is None else delay

    for test_data in suite_data:
        logging.info(f"Sending report for test {test_data['id']} to simulate {test_data['doc']}")
        if "dag_id" not in test_data["message"]["payload"]:
            test_data["message"]["payload"]["dag_id"] = dag_id
        if "run_id" not in test_data["message"]["payload"]:
            test_data["message"]["payload"]["run_id"] = run_id
        REPORT_CATEGORIES[test_data["category"]](
            message=test_data["message"],
            **test_data.get("params", {})
        )
        sleep(delay)


def get_simulation_thread(suite_data, dag_id, run_id):
    return threading.Thread(
        target=send_reports,
        daemon=True,
        kwargs={
            "suite_data": suite_data,
            "dag_id": dag_id,
            "run_id": run_id
        }
    )

def get_start_date(suite_data, default=None):
    """
    Tries to find start_date from the reported workflow execution statistics.
    If we failed to find it, use default from utcnow()
    """

    start_date = utcnow() if default is None else default
    for test_data in suite_data:
        try:
            start_date = parsedate(test_data["message"]["payload"]["statistics"]["total"]["start_date"])
        except Exception:
            pass
    return start_date


def run_workflow_execution_simulation(suite_data, dag_id, run_id):
    simulation_thread = get_simulation_thread(
        suite_data=suite_data,
        dag_id=dag_id,
        run_id=run_id
    )
    simulation_thread.start()
    start_date = get_start_date(suite_data)
    return {
        "dag_id": dag_id,
        "run_id": run_id,
        "execution_date": start_date,
        "start_date": start_date,
        "state": State.RUNNING
    }
