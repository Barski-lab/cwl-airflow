import os
import logging
import psutil
import shutil

from datetime import datetime
from airflow import configuration
from airflow.models import DAG, DagRun, TaskInstance
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago
from airflow.utils.db import provide_session
from airflow.utils.state import State
from airflow.settings import DAGS_FOLDER
from airflow.utils.dag_processing import list_py_file_paths
from airflow.api.common.experimental import delete_dag

from cwl_airflow.utilities.report import dag_on_success, dag_on_failure
from cwl_airflow.utilities.helpers import load_yaml, get_rootname


TIMEOUT = configuration.conf.getint("core", "KILLED_TASK_CLEANUP_TIME")


@provide_session
def clean_db(dr, session=None):
    logging.info(f"""Cleaning DB for dag_id: {dr.dag_id}, run_id: {dr.run_id}""")
    for ti in dr.get_task_instances():
        logging.info(f"""Task: {ti.task_id}, execution_date: {ti.execution_date}, pid: {ti.pid}, state: {ti.state}""")
        logging.info(" - cleaning Xcom table")
        ti.clear_xcom_data()
        logging.info(" - cleaning TaskInstance table")
        session.query(TaskInstance).filter(
            TaskInstance.task_id == ti.task_id,
            TaskInstance.dag_id == ti.dag_id,
            TaskInstance.execution_date == dr.execution_date).delete(synchronize_session="fetch")
        session.commit()
    logging.info("cleaning DagRun table")
    session.query(DagRun).filter(
        DagRun.dag_id == dr.dag_id,
        DagRun.run_id == dr.run_id,
    ).delete(synchronize_session="fetch")
    session.commit()


def stop_tasks(dr):
    logging.info(f"""Stopping running tasks for dag_id: {dr.dag_id}, run_id: {dr.run_id}""")
    for ti in dr.get_task_instances():
        logging.info(f"""Task: {ti.task_id}, execution_date: {ti.execution_date}, pid: {ti.pid}, state: {ti.state}""")
        if ti.state == State.RUNNING:
            try:
                logging.info(" - searching for process by pid")
                process = psutil.Process(ti.pid) if ti.pid else None
            except Exception:
                logging.info(" - cannot find process by pid")
                process = None
            logging.info(" - setting state to failed")
            ti.set_state(State.FAILED)
            if process:
                logging.info(" - waiting for process to exit")
                try:
                    process.wait(timeout=TIMEOUT * 2)  # raises psutil.TimeoutExpired if timeout. Makes task fail -> DagRun fails
                except psutil.TimeoutExpired as e:
                    logging.info(" - done waiting for process to die, giving up")


def remove_tmp_data(dr):
    logging.info(f"""Searching tmp data for dag_id: {dr.dag_id}, run_id: {dr.run_id}""")
    tmp_folder_set = set()
    for ti in dr.get_task_instances():
        logging.info(f"""Task: {ti.task_id}, execution_date: {ti.execution_date}, pid: {ti.pid}, state: {ti.state}""")
        try:
            logging.info(" - searching for tmp_folder in the report file")
            report_location = ti.xcom_pull(task_ids=ti.task_id)
            tmp_folder_set.add(load_yaml(report_location)["tmp_folder"])
        except Exception:
            logging.info(" - report file has been already deleted or it's missing tmp_folder field")
    for tmp_folder in tmp_folder_set:
        try:
            logging.info(f"""Removing tmp data from {tmp_folder}""")
            shutil.rmtree(tmp_folder)
        except Exception as ex:
            logging.error(f"""Failed to delete {tmp_folder}\n {ex}""")


def remove_outdated_dags(cwl_id):
    logging.info(f"""Searching for dags based on cwl_id: {cwl_id}""")
    dags = {}
    for location in list_py_file_paths(DAGS_FOLDER, include_examples=False):
        dag_id = get_rootname(location)
        if cwl_id not in dag_id:
            continue
        dags[dag_id] = {
            "location": location,
            "modified": datetime.fromtimestamp(os.path.getmtime(location))
        }
        logging.info(f"""Found dag_id: {dag_id}, modified: {dags[dag_id]["modified"]}""")
    for dag_id, dag_metadata in sorted(dags.items(), key=lambda i: i[1]["modified"])[:-1]:
        logging.info(f"""Cleaning dag_id: {dag_id}""")
        if len(DagRun.find(dag_id=dag_id, state=State.RUNNING)) == 0:
            try:
                delete_dag.delete_dag(dag_id)
            except Exception as ex:
                logging.error(f"""Failed to delete DAG\n {ex}""")
            for f in [
                dag_metadata["location"],
                os.path.splitext(dag_metadata["location"])[0]+".cwl"
            ]:
                try:
                    logging.info(f"""Deleting DAG file: {f}""")
                    os.remove(f)
                except Exception as ex:
                    logging.error(f"""Failed to delete file {f}\n {ex}""")
        else:
            logging.info("Skipping, DAG has running DagRuns")


def clean_dag_run(**context):
    dag_id = context["dag_run"].conf["remove_dag_id"]
    run_id = context["dag_run"].conf["remove_run_id"]
    dr_list = DagRun.find(dag_id=dag_id, run_id=run_id)
    for dr in dr_list:
        stop_tasks(dr)
        remove_tmp_data(dr)
        clean_db(dr)
    remove_outdated_dags(dag_id.split("-")[0])


dag = DAG(dag_id="clean_dag_run",
          start_date=days_ago(1),
          on_failure_callback=dag_on_failure,
          on_success_callback=dag_on_success,
          schedule_interval=None)


run_this = PythonOperator(task_id="clean_dag_run",
                          python_callable=clean_dag_run,
                          provide_context=True,
                          dag=dag)
