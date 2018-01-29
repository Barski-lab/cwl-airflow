import logging
from airflow.models import BaseOperator, TaskInstance
from airflow.utils import apply_defaults
import os
from jsonmerge import merge
import cwltool.errors
import shutil
import json
from cwl_airflow.modules.cwlutils import set_permissions

class JobCleanup(BaseOperator):

    # ui_color = '#3E53B7'
    # ui_fgcolor = '#FFF'

    @apply_defaults
    def __init__(
            self,
            outputs,
            rm_files=None,
            rm_files_dest_folder=None,
            op_args=None,
            op_kwargs=None,
            *args, **kwargs):
        super(JobCleanup, self).__init__(*args, **kwargs)

        self.op_args = op_args or []
        self.op_kwargs = op_kwargs or {}
        self.outputs = outputs
        self.outdir = None
        self.output_folder = self.dag.default_args["output_folder"]
        self.rm_files = rm_files or []
        self.rm_files_dest_folder = rm_files_dest_folder

    def execute(self, context):
        upstream_task_ids = [t.task_id for t in self.upstream_list]
        upstream_data = self.xcom_pull(context=context, task_ids=upstream_task_ids)

        logging.info('{0}: Collecting outputs from: \n {1}'.format(self.task_id, json.dumps(upstream_task_ids, indent=4)))

        promises = {}
        for j in upstream_data:
            data = j
            promises = merge(promises, data["promises"])
            if "outdir" in data:
                self.outdir = data["outdir"]

        if promises and not self.outdir:
            raise cwltool.errors.WorkflowException("Outdir is not provided, please use job dispatcher")

        logging.info('{0}: with data: \n {1}'.format(self.task_id, json.dumps(promises, indent=4)))

        logging.info('{0}: Moving data for workflow outputs: \n {1}'.format(self.task_id, json.dumps(self.outputs, indent=4)))

        def visit(item):
            item_list.append(item["location"])
            visit_sublist(item.get("secondaryFiles", []))

        def visit_sublist(sublist):
            for item in sublist:
                visit(item)

        collected_workflow_outputs = {}

        for out,val in self.outputs.iteritems():
            if out in promises:
                collected_workflow_outputs = merge(collected_workflow_outputs, {val.split("/")[-1]: promises[out]})
                if isinstance(promises[out], dict) and "class" in promises[out] and promises[out]["class"] in ['File', 'Directory']:
                    item_list = []
                    visit(promises[out])
                    for item in item_list:
                        src = item.replace("file://",'')
                        dst = os.path.join(self.output_folder, os.path.basename(src))
                        logging.info('{0}: Moving: \n {1} --> {2}'.format(self.task_id, src, dst))
                        if os.path.exists(dst):
                            os.remove(dst) if promises[out]["class"] == 'File' else shutil.rmtree (dst, True)
                        shutil.move(src, dst)
                        set_permissions(dst, dir_perm=0775, file_perm=0664)

        for rmf in self.rm_files:
            if os.path.isfile(rmf):
                if self.rm_files_dest_folder:
                    os.rename(rmf, os.path.join(self.rm_files_dest_folder, os.path.basename(rmf)))
                    logging.info('{0}: Job file {1} is moved to {2}'.format(self.task_id, rmf, self.rm_files_dest_folder))
                else:
                    os.remove(rmf)
                    logging.info('{0}: Job file {1} is deleted'.format(self.task_id, rmf))
        try:
            shutil.rmtree(self.outdir, ignore_errors=False)
            logging.info('{0}: Delete temporary output directory {1}'.format(self.task_id, self.outdir))
        except:
            logging.info("{0}: Temporary output directory hasn't been set".format(self.task_id))

        print "WORKFLOW RESULTS"
        print json.dumps(collected_workflow_outputs, indent=4)
