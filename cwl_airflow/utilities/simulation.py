#! /usr/bin/env python3
import threading
import logging

from time import sleep

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


def send_reports(simulation_data, dag_id, run_id):
    for test_data in simulation_data:
        logging.info(f"Sending report for test {test_data['id']} to simulate {test_data['doc']}")
        test_data["message"]["payload"]["dag_id"] = dag_id
        test_data["message"]["payload"]["run_id"] = run_id
        REPORT_CATEGORIES[test_data["category"]](
            message=test_data["message"],
            **test_data.get("params", {})
        )
        sleep(3)


def get_simulation_thread(simulation_data, dag_id, run_id):
    return threading.Thread(
        target=send_reports,
        daemon=True,
        kwargs={
            "simulation_data": simulation_data,
            "dag_id": dag_id,
            "run_id": run_id
        }
    )


def run_simulation(simulation_data, dag_id, run_id):
    simulation_thread = get_simulation_thread(
        simulation_data=simulation_data,
        dag_id=dag_id,
        run_id=run_id
    )
    simulation_thread.start()


