#! /usr/bin/env python3
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults

from cwl_airflow.utilities.cwl import (
    relocate_outputs,
    collect_reports
)
from cwl_airflow.utilities.report import post_status
from cwl_airflow.utilities.loggers import setup_cwl_logger


class CWLJobGatherer(BaseOperator):

    @apply_defaults  # in case someone decided to overwrite default_args from the DAG
    def __init__(
        self,
        task_id,
        *args, **kwargs
    ):
        super().__init__(task_id=task_id, *args, **kwargs)
        

    def execute(self, context):
        """
        Loads and merges data from report files of all finished tasks in a DAG.
        Relocates results to the "outputs_folder", removes "tmp_folder"
        """

        setup_cwl_logger(context["ti"])
        post_status(context)

        _, workflow_report = relocate_outputs(
            workflow=context["dag"].workflow,
            job_data=collect_reports(context),
            cwl_args=context["dag"].default_args["cwl"],
        )
     
        return workflow_report
