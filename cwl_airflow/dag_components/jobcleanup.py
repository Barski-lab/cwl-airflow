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
        tmp_folder = collected_outputs["tmp_folder"]
        output_folder = collected_outputs["output_folder"]
        relocated_outputs = relocateOutputs(outputObj={output_id: collected_outputs[output_src]
                                                       for output_src, output_id in self.dag.get_output_list().items()
                                                       if output_src in collected_outputs},
                                            outdir=output_folder,
                                            output_dirs=[output_folder],
                                            action="copy",
                                            fs_access=StdFsAccess(""))

        relocated_outputs = {key.split("/")[-1]: val for key, val in relocated_outputs.items()}
        shutil.rmtree(tmp_folder, ignore_errors=False)
        logging.debug('Delete temporary output directory {}'.format(tmp_folder))
        logging.info("WORKFLOW RESULTS\n" + json.dumps(relocated_outputs, indent=4))
