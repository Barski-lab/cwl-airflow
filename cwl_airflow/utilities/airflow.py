#! /usr/bin/env python3
from jsonmerge import merge
from airflow.configuration import conf
from airflow.exceptions import AirflowConfigException

from cwl_airflow.utilities.cwl import load_job


DAG_TEMPLATE="""#!/usr/bin/env python3
from cwl_airflow.extensions.cwldag import CWLDAG
dag = CWLDAG(workflow="{0}", dag_id="{1}")
"""


def conf_get(section, key, default):
    """
    Return value from AirflowConfigParser object.
    If section or key is absent, return default
    """

    try:
        return conf.get(section, key)
    except AirflowConfigException:
        return default


def collect_reports(context, cwl_args, task_ids=None):
    """
    Collects reports from "context" for specified "task_ids".
    If "task_ids" was not set, use all tasks from DAG.
    Loads and merges data from reports.
    """

    task_ids = context["dag"].task_ids if task_ids is None else task_ids

    job_data = {}
    for report_location in context["ti"].xcom_pull(task_ids=task_ids):
        if report_location is not None:
            report_data = load_job(
                cwl_args,                 # should be ok even if cwl_args["workflow"] points to the original workflow
                report_location           # as all defaults from it should have been already added by dispatcher
            )
            job_data = merge(job_data, report_data)
    
    return job_data