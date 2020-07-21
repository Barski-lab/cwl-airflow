#!/usr/bin/env python3
from airflow.models import DAG
from airflow.utils.dates import days_ago

dag = DAG(
    dag_id="dummy_dag",
    start_date=days_ago(1),
    schedule_interval=None
)