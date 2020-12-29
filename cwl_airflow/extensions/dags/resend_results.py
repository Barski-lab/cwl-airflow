import logging

from airflow.models import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.utils import timezone
from airflow.models import Variable
from airflow.utils.session import create_session

from cwl_airflow.utilities.report import http_hook


def resend_results():
    with create_session() as session:
        for var in session.query(Variable):
            if any(prefix in var.key for prefix in ["post_progress", "post_results"]):
                logging.info(f"Retreive {var.key} from Variables")
                value = Variable.get(key=var.key, deserialize_json=True)
                try:
                    http_hook.run(endpoint=value["endpoint"], json=value["message"])
                    Variable.delete(key=var.key)
                    logging.info(f"Value from {var.key} variable has been successfully sent")
                except Exception as err:
                    logging.info(f"Failed to POST value from {var.key} variable. Will retry in the next run \n {err}")


dag = DAG(dag_id="resend_results",
          start_date=timezone.datetime(2020, 1, 1),  # any fixed date in the past. Doens't matter as we set catchup to False
          schedule_interval="*/10 * * * *",          # every 10 minutes
          catchup=False,
          is_paused_upon_creation=True,              # no need to automatically run it if user didn't even add process_report connection
          max_active_runs=1
)


run_this = PythonOperator(
    task_id="resend_results",
    python_callable=resend_results,
    dag=dag
)
