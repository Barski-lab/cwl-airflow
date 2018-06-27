import json
import logging
from airflow.models import BaseOperator


class JobDispatcher(BaseOperator):

    def __init__(self, *args, **kwargs):
        super(JobDispatcher, self).__init__(task_id=self.__class__.__name__, *args, **kwargs)

    def execute(self, context):
        job_object = self.dag.default_args["job_data"]["content"]
        logging.info("Dispatch job\n{}".format(json.dumps(job_object, indent=4)))
        return {"outputs": job_object}
