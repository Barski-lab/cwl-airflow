#! /usr/bin/env python3
from copy import deepcopy
from jsonmerge import merge

from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults

from cwl_airflow.utilities.cwl import (
    execute_workflow_step,
    load_job
)

# from cwl_airflow.utilities.report import post_status


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
        Loads data from report files of all upstream tasks. Merge them into a single job
        and executes a workflow constracted from the workflow step. Writes to X-Com report
        file location.
        """

        # post_status(context)

        # for easy access
        default_args = context["dag"].default_args
        cwl_args = default_args["cwl"]

        job_data = {}
        for upstream_report in self.xcom_pull(context=context, task_ids=self.upstream_task_ids):
            upstream_outputs = load_job(
                cwl_args,                 # should be ok even if cwl_args["workflow"] points to the original workflow
                upstream_report           # as all defaults from it should have been already added by dispatcher
            )                                                           
            job_data = merge(job_data, upstream_outputs)

        _, step_report = execute_workflow_step(
            cwl_args,
            job_data,
            self.task_id
        )

        return step_report









    # def on_kill(self):
    #     _logger.info("Stop docker containers")
    #     for cidfile in glob.glob(os.path.join(self.dag.default_args["cidfile_dir"], self.task_id + "*.cid")):  # make this better, doesn't look good to read from self.dag.default_args
    #         try:
    #             with open(cidfile, "r") as inp_stream:
    #                 _logger.debug(f"""Read container id from {cidfile}""")
    #                 command = ["docker", "kill", inp_stream.read()]
    #                 _logger.debug(f"""Call {" ".join(command)}""")
    #                 p = subprocess.Popen(command, shell=False)
    #                 try:
    #                     p.wait(timeout=10)
    #                 except subprocess.TimeoutExpired:
    #                     p.kill()
    #         except Exception as ex:
    #             _logger.error(f"""Failed to stop docker container with ID from {cidfile}\n {ex}""")

    #     # _logger.info(f"""Delete temporary output directory {self.outdir}""")
    #     # try:
    #     #     shutil.rmtree(self.outdir)
    #     # except Exception as ex:
    #     #     _logger.error(f"""Failed to delete temporary output directory {self.outdir}\n {ex}""")
