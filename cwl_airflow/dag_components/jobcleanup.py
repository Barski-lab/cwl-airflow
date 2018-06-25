import os
import json
import shutil
import logging
from jsonmerge import merge
from airflow.models import BaseOperator
from cwl_airflow.utils.utils import set_permissions


class JobCleanup(BaseOperator):

    def __init__(
            self,
            outputs,
            op_args=None,
            op_kwargs=None,
            *args, **kwargs):
        super(JobCleanup, self).__init__(*args, **kwargs)

        self.op_args = op_args or []
        self.op_kwargs = op_kwargs or {}
        self.outputs = outputs

    def execute(self, context):
        upstream_task_ids = [t.task_id for t in self.upstream_list]
        upstream_data = self.xcom_pull(context=context, task_ids=upstream_task_ids)

        logging.info('{0}: Collecting outputs from: \n {1}'.format(self.task_id, json.dumps(upstream_task_ids, indent=4)))

        promises = {}
        for j in upstream_data:
            data = j
            promises = merge(promises, data["promises"])

        logging.info('{0}: with data: \n {1}'.format(self.task_id, json.dumps(promises, indent=4)))
        logging.info('{0}: Moving data for workflow outputs: \n {1}'.format(self.task_id, json.dumps(self.outputs, indent=4)))

        def visit(item):
            item_list.append(item["location"])
            visit_sublist(item.get("secondaryFiles", []))

        def visit_sublist(sublist):
            for item in sublist:
                visit(item)

        collected_workflow_outputs = {}

        for out,val in self.outputs.items():
            if out in promises:
                collected_workflow_outputs = merge(collected_workflow_outputs, {val.split("/")[-1]: promises[out]})
                if isinstance(promises[out], dict) and "class" in promises[out] and promises[out]["class"] in ['File', 'Directory']:
                    item_list = []
                    visit(promises[out])
                    for item in item_list:
                        src = item.replace("file://", '')
                        dst = os.path.join(self.dag.default_args["output_folder"], os.path.basename(src))
                        logging.info('{0}: Moving: \n {1} --> {2}'.format(self.task_id, src, dst))
                        if os.path.exists(dst):
                            os.remove(dst) if promises[out]["class"] == 'File' else shutil.rmtree (dst, True)
                        shutil.move(src, dst)
                        set_permissions(dst, dir_perm=0o0775, file_perm=0o0664)

        shutil.rmtree(self.dag.default_args["tmp_folder"], ignore_errors=False)
        logging.debug('{0}: Delete temporary output directory {1}'.format(self.task_id, self.dag.default_args["tmp_folder"]))
        logging.info("WORKFLOW RESULTS\n" + json.dumps(collected_workflow_outputs, indent=4))
