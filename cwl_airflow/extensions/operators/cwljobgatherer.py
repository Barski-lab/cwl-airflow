#! /usr/bin/env python3
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults

# from cwl_airflow.utilities.report import post_status


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
        Loads data from all reports from upstream tasks. Combines then into a single
        file and rellocato to the "outputs_folder". Temp data is removed.
        """

        # post_status(context)

        # for easy access
        default_args = context["dag"].default_args
        cwl_args = default_args["cwl"]

        job_data = {}
        for upstream_report in self.xcom_pull(context=context, task_ids=self.upstream_task_ids):
            upstream_outputs = load_job(
                cwl_args,                 # should be ok even if cwl_args["workflow"] points to the original workflow
                upstream_report
            )                                                           
            job_data = merge(job_data, upstream_outputs)

        print("job_data", job_data)

        # try:
        #     if self.outdir:
        #         shutil.rmtree(self.outdir, ignore_errors=False)
        # except Exception as e:
        #     pass

        return job_data
