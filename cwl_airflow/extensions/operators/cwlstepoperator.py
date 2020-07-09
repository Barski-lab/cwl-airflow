#! /usr/bin/env python3
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults

from cwl_airflow.utilities.cwl import (
    execute_workflow_step,
    collect_reports
)
from cwl_airflow.utilities.report import post_status


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

        post_status(context)

        _, step_report = execute_workflow_step(
            workflow=context["dag"].workflow,
            task_id=self.task_id,
            job_data=collect_reports(context),
            cwl_args=context["dag"].default_args["cwl"]
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
