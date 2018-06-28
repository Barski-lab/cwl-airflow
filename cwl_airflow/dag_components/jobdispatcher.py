import sys
import json
import logging
from argparse import Namespace
from airflow.models import BaseOperator
from cwltool.main import init_job_order
from cwltool.load_tool import jobloaderctx
from schema_salad.ref_resolver import Loader


class JobDispatcher(BaseOperator):

    def __init__(self, *args, **kwargs):
        super(JobDispatcher, self).__init__(task_id=self.__class__.__name__, *args, **kwargs)

    def execute(self, context):
        initialized_job_order_object = init_job_order(self.dag.default_args["job_data"]["content"],
                                                      Namespace(),
                                                      self.dag.cwlwf,
                                                      Loader(jobloaderctx.copy()),
                                                      sys.stdout)
        logging.info("Dispatch job\n{}".format(json.dumps(initialized_job_order_object, indent=4)))
        return {"outputs": initialized_job_order_object}
