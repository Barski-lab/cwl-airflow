#! /usr/bin/env python3
import os
from tempfile import mkdtemp

from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults

from cwl_airflow.utilities.helpers import (
    get_dir,
    dump_json,
    get_absolute_path
)
from cwl_airflow.utilities.cwl import (
    load_job,
    get_temp_folders
)
from cwl_airflow.utilities.report import post_status
from cwl_airflow.utilities.loggers import setup_cwl_logger


class CWLJobDispatcher(BaseOperator):


    @apply_defaults  # in case someone decided to overwrite default_args from the DAG
    def __init__(
        self,
        task_id,
        *args, **kwargs
    ):
        super().__init__(task_id=task_id, *args, **kwargs)


    def execute(self, context):
        """
        Loads job Object from the context. Sets "tmp_folder" and "output_folder"
        if they have not been set before in the job. In case "tmp_folder" and/or
        "output_folder" were read from the job and are relative, resolves paths
        relative to the "tmp_folder" and/or "outputs_folder" from "cwl_args".
        Dumps step outputs as a json file into "tmp_folder". Writes to X-Com report
        file location.
        """

        setup_cwl_logger(context["ti"])
        post_status(context)

        # for easy access
        dag_id = context["dag"].dag_id
        workflow = context["dag"].workflow
        run_id = context["run_id"].replace(":", "_").replace("+", "_")  # to make it dumpable by json
        cwl_args = context["dag"].default_args["cwl"]

        # Loads job from dag_run configuration. Sets defaults from "workflow". Fails on missing input files
        job_data = load_job(
            workflow=workflow,
            job=context["dag_run"].conf["job"],
            cwl_args=cwl_args
        )

        job_data["tmp_folder"] = get_dir(
            get_absolute_path(
                job_data.get(
                    "tmp_folder",
                    mkdtemp(
                        dir=cwl_args["tmp_folder"],
                        prefix=dag_id+"_"+run_id+"_"
                    )
                ),
                cwl_args["tmp_folder"]
            )
        )

        job_data["outputs_folder"] = get_dir(
            get_absolute_path(
                job_data.get(
                    "outputs_folder",
                    os.path.join(
                        cwl_args["outputs_folder"],
                        dag_id,
                        run_id
                    )
                ),
                cwl_args["outputs_folder"]
            )
        )

        _, _, _, step_report = get_temp_folders(
            task_id=self.task_id,
            job_data=job_data
        )

        dump_json(job_data, step_report)

        return step_report
