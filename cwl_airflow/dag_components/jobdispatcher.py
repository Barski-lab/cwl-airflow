import sys
import json
import logging
import tempfile
from argparse import Namespace
from airflow.models import BaseOperator
from cwltool.main import init_job_order
from cwltool.load_tool import jobloaderctx
from schema_salad.ref_resolver import Loader
from cwl_airflow.utils.utils import shortname

class JobDispatcher(BaseOperator):

    def __init__(self, *args, **kwargs):
        super(JobDispatcher, self).__init__(task_id=self.__class__.__name__, *args, **kwargs)

    def execute(self, context):
        initialized_job_order_object = init_job_order(self.dag.default_args["job_data"]["content"],
                                                      Namespace(),
                                                      self.dag.cwlwf,
                                                      Loader(jobloaderctx.copy()),
                                                      sys.stdout)

        updated_job_order_object = {}
        for index, inp in enumerate(self.dag.cwlwf.tool["inputs"]):
            inp_id = shortname(inp["id"])
            if inp_id.split("/")[-1] in initialized_job_order_object:
                updated_job_order_object[inp_id] = initialized_job_order_object[inp_id.split("/")[-1]]

        updated_job_order_object["tmp_folder"] = tempfile.mkdtemp(dir=self.dag.default_args["job_data"]["content"].get("tmp_folder", None), prefix="dag_tmp_")
        updated_job_order_object["output_folder"] = self.dag.default_args["job_data"]["content"]["output_folder"]
        logging.info("Dispatch job\n{}".format(json.dumps(updated_job_order_object, indent=4)))
        return {"outputs": updated_job_order_object}
