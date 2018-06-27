import json
import shutil
import logging
from jsonmerge import merge
from airflow.models import BaseOperator
from cwltool.process import relocateOutputs
from cwltool.stdfsaccess import StdFsAccess


class JobCleanup(BaseOperator):

    def __init__(self, *args, **kwargs):
        super(JobCleanup, self).__init__(task_id=self.__class__.__name__, *args, **kwargs)

    def execute(self, context):
        collected_outputs = {}
        for task_outputs in self.xcom_pull(context=context, task_ids=[task.task_id for task in self.upstream_list]):
            collected_outputs = merge(collected_outputs, task_outputs["outputs"])
        logging.debug('Collected outputs:\n{}'.format(json.dumps(collected_outputs, indent=4)))
        relocated_outputs = relocateOutputs(outputObj={out_name.split("/")[-1]: collected_outputs[out_name]
                                                       for out_name in self.dag.get_output_list().keys()
                                                       if out_name in collected_outputs},
                                            outdir=self.dag.default_args["job_data"]["content"]["output_folder"],
                                            output_dirs=[self.dag.default_args["job_data"]["content"]["output_folder"]],
                                            action="move",
                                            fs_access=StdFsAccess(""))
        shutil.rmtree(self.dag.default_args["tmp_folder"], ignore_errors=False)
        logging.debug('Delete temporary output directory {}'.format(self.dag.default_args["tmp_folder"]))
        logging.info("WORKFLOW RESULTS\n" + json.dumps(relocated_outputs, indent=4))
