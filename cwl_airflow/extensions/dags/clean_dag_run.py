import logging
import psutil
import shutil

from cwl_airflow.utilities.report import dag_on_success, dag_on_failure
from cwl_airflow.utilities.helpers import CleanAirflowImport

with CleanAirflowImport():
    from airflow import configuration
    from airflow.models import DAG, DagRun, TaskInstance
    from airflow.operators.python_operator import PythonOperator
    from airflow.utils.dates import days_ago
    from airflow.utils.db import provide_session
    from airflow.utils.state import State



logger = logging.getLogger(__name__)


TIMEOUT = configuration.conf.getint('core', 'KILLED_TASK_CLEANUP_TIME')


@provide_session
def clean_db(dr, session=None):
    logger.debug(f"""Clean DB for {dr.dag_id} - {dr.run_id}""")
    for ti in dr.get_task_instances():
        logger.debug(f"""process {ti.dag_id} - {ti.task_id} - {ti.execution_date}""")
        ti.clear_xcom_data()
        logger.debug(" - clean Xcom table")
        session.query(TaskInstance).filter(
            TaskInstance.task_id == ti.task_id,
            TaskInstance.dag_id == ti.dag_id,
            TaskInstance.execution_date == dr.execution_date).delete(synchronize_session='fetch')
        session.commit()
        logger.debug(" - clean TaskInstance table")
    session.query(DagRun).filter(
        DagRun.dag_id == dr.dag_id,
        DagRun.run_id == dr.run_id,
    ).delete(synchronize_session='fetch')
    session.commit()
    logger.debug(" - clean dag_run table")


def stop_tasks(dr):
    logger.debug(f"""Stop tasks for {dr.dag_id} - {dr.run_id}""")
    for ti in dr.get_task_instances():
        logger.debug(f"""process {ti.dag_id} - {ti.task_id} - {ti.execution_date} - {ti.pid}""")
        if ti.state == State.RUNNING:
            try:
                process = psutil.Process(ti.pid) if ti.pid else None
            except Exception:
                logger.debug(f" - cannot find process by PID {ti.pid}")
                process = None
            ti.set_state(State.FAILED)
            logger.debug(" - set state to FAILED")
            if process:
                logger.debug(f" - wait for process {ti.pid} to exit")
                try:
                    process.wait(timeout=TIMEOUT * 2)  # raises psutil.TimeoutExpired if timeout. Makes task fail -> DagRun fails
                except psutil.TimeoutExpired as e:
                    logger.debug(f" - Done waiting for process {ti.pid} to die")


def remove_tmp_data(dr):
    logger.debug(f"""Remove tmp data for {dr.dag_id} - {dr.run_id}""")
    tmp_folder_set = set()
    for ti in dr.get_task_instances():
        ti_xcom_data = ti.xcom_pull(task_ids=ti.task_id) # can be None
        if ti_xcom_data and "outdir" in ti_xcom_data:
            tmp_folder_set.add(ti_xcom_data["outdir"])
    for tmp_folder in tmp_folder_set:
        try:
            shutil.rmtree(tmp_folder)
            logger.debug(f"""Successfully removed {tmp_folder}""")
        except Exception as ex:
            logger.error(f"""Failed to delete temporary output directory {tmp_folder}\n {ex}""")


def clean_dag_run(**context):
    dag_id = context['dag_run'].conf['remove_dag_id']
    run_id = context['dag_run'].conf['remove_run_id']
    dr_list = DagRun.find(dag_id=dag_id, run_id=run_id)
    for dr in dr_list:
        stop_tasks(dr)
        remove_tmp_data(dr)
        clean_db(dr)
        


dag = DAG(dag_id="clean_dag_run",
          start_date=days_ago(1),
          on_failure_callback=dag_on_failure,
          on_success_callback=dag_on_success,
          schedule_interval=None)


run_this = PythonOperator(task_id='clean_dag_run',
                          python_callable=clean_dag_run,
                          provide_context=True,
                          dag=dag)


