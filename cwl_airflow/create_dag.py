#!/usr/bin/env python
import os
from airflow.configuration import conf
from cwl_airflow.utils.func import make_dag


def create_dags():
    dags_dict = {}
    for job_file in os.listdir(conf.get('biowardrobe', 'jobs')):
        kwargs = {"job": os.path.join(conf.get('biowardrobe', 'jobs'), job_file), "ignore_def_outdir": True}
        dags_dict[job_file] = make_dag(kwargs)
    return dags_dict
