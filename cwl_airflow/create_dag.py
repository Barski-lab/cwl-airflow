#!/usr/bin/env python
from airflow import configuration
from cwl_airflow.utils.func import make_dag, get_active_jobs


def create_dags():
    dags = {}
    for job in get_active_jobs(jobs_folder=configuration.get('cwl', 'jobs'), limit=int(configuration.get('cwl', 'limit'))):
        try:
            dags[job["dag_id"]] = make_dag(job)
        except Exception:
            pass
    return dags
