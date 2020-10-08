#! /usr/bin/env python3
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults

from cwl_airflow.utilities.cwl import (
    execute_workflow_step,
    get_containers,
    kill_containers,
    collect_reports
)
from cwl_airflow.utilities.report import post_status
from cwl_airflow.utilities.loggers import setup_cwl_logger


class CWLStepOperator(BaseOperator):


    @apply_defaults  # in case someone decided to overwrite default_args from the DAG
    def __init__(
        self,
        task_id,
        *args, **kwargs
    ):
        super().__init__(task_id=task_id, *args, **kwargs)


    def execute(self, context):
        """
        Creates job from collected reports of all finished tasks in a DAG.
        Then executes a workflow constructed from the workflow step. Writes
        report file location to X-Com.
        """

        setup_cwl_logger(context["ti"])
        post_status(context)

        self.job_data = collect_reports(context)         # we need it also in "on_kill"
        _, step_report = execute_workflow_step(
            workflow=context["dag"].workflow,
            task_id=self.task_id,
            job_data=self.job_data,
            cwl_args=context["dag"].default_args["cwl"]
        )

        return step_report


    def on_kill(self):
        """
        Function is called only if task is manually stopped, for example, from UI.
        First, we need to find all cidfiles that correspond to the current step.
        We can have more than one cidfile, if previous run of this step has failed.
        We search for cidfiles in the subfolder "task_id" of the "tmp_folder" read
        from "job_data". For all found cidfile we check if cointainer is still
        running and try to stop it. If container was not running, was not found or
        had been already successfully killed, we remove the correspondent cidfile.
        If container was running but we failed to kill it do not remove cidfile.
        """

        kill_containers(
            get_containers(self.job_data, self.task_id)
        )
