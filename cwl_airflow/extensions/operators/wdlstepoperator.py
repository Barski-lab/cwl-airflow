#! /usr/bin/env python3
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from airflow.exceptions import AirflowSkipException
from airflow.models.xcom import XCOM_RETURN_KEY

from cwl_airflow.utilities.wdl import (
    execute_workflow_step,
    get_containers,
    kill_containers,
    collect_reports
)
from cwl_airflow.utilities.report import post_status
from cwl_airflow.utilities.loggers import setup_cwl_logger


class WDLStepOperator(BaseOperator):

    @apply_defaults  # in case someone decided to overwrite default_args from the DAG
    def __init__(
        self,
        task_id,
        *args, **kwargs
    ):
        # change default trigger_rule as the upstream can be skipped
        super().__init__(task_id=task_id, trigger_rule="none_failed", *args, **kwargs)

    def execute(self, context):
        """
        Creates job from collected reports of all finished tasks in a DAG.
        Then executes a workflow constructed from the workflow step. Writes
        report file location to X-Com.
        """
        step_report = {}

        return step_report
