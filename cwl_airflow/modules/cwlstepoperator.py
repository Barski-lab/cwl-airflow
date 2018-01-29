#
# CWLStepOperator is required for CWLDAG
#   CWLStepOperator execute stage expects input job from xcom_pull
#   and post output by xcom_push

import cwltool.main
import cwltool.workflow
import cwltool.errors
import logging
from airflow.models import BaseOperator
from airflow.utils import (apply_defaults)
from jsonmerge import merge
import json
import os
import copy
from cwl_airflow.modules.cwlutils import shortname, flatten
import tempfile
import cwltool.stdfsaccess


class CWLStepOperator(BaseOperator):

    ui_color = '#3E53B7'
    ui_fgcolor = '#FFF'

    @apply_defaults
    def __init__(
            self,
            cwl_step,
            ui_color=None,
            op_args=None,
            op_kwargs=None,
            *args, **kwargs):

        self.outdir = None

        self.cwl_step = cwl_step
        step_id = shortname(cwl_step.tool["id"]).split("/")[-1]

        super(self.__class__, self).__init__(task_id=step_id, *args, **kwargs)

        self.op_args = op_args or []
        self.op_kwargs = op_kwargs or {}

        if ui_color:
            self.ui_color = ui_color

    def execute(self, context):

        logging.info('{0}: Running tool: \n{1}'.format(self.task_id, json.dumps(self.cwl_step.embedded_tool.tool, indent=4)))

        upstream_task_ids = [t.task_id for t in self.upstream_list]
        upstream_data = self.xcom_pull(context=context, task_ids=upstream_task_ids)

        logging.info('{0}: Collecting outputs from: \n{1}'.format(self.task_id, json.dumps(upstream_task_ids, indent=4)))

        promises = {}
        for j in upstream_data:
            data = j
            promises = merge(promises, data["promises"])
            if "outdir" in data:
                self.outdir = data["outdir"]

        if not self.outdir:
            raise cwltool.errors.WorkflowException("Outdir is not provided, please use job dispatcher")

        logging.info(
            '{0}: Upstream data: \n {1}'.format(self.task_id, json.dumps(upstream_data,indent=4)))

        logging.info(
            '{0}: Step inputs: \n {1}'.format(self.task_id, json.dumps(self.cwl_step.tool["inputs"],indent=4)))

        logging.info(
            '{0}: Step outputs: \n {1}'.format(self.task_id, json.dumps(self.cwl_step.tool["outputs"],indent=4)))

        jobobj = {}

        for inp in self.cwl_step.tool["inputs"]:
            jobobj_id = shortname(inp["id"]).split("/")[-1]
            source_ids = []
            promises_outputs = []
            try:
                source_ids = [shortname(source) for source in inp["source"]] if isinstance(inp["source"], list) else [shortname(inp["source"])]
                promises_outputs = [promises[source_id] for source_id in source_ids if source_id in promises]
            except Exception as ex:
                logging.info("{0}: Couldn't find source field in step input:\n{1}".format(self.task_id,json.dumps(inp,indent=4)))
            logging.info('{0}: For input {1} with source_ids: {2} found upstream outputs: \n{3}'.format(self.task_id, jobobj_id, source_ids, promises_outputs))
            if len(promises_outputs) > 1:
                if inp.get("linkMerge", "merge_nested") == "merge_flattened":
                    jobobj[jobobj_id] = flatten (promises_outputs)
                else:
                    jobobj[jobobj_id] = promises_outputs
            elif len(promises_outputs) == 1 and (promises_outputs[0] is not None): # Should also check if [None], because in this case we need to take default value
                jobobj[jobobj_id] = promises_outputs[0]
            elif "valueFrom" in inp:
                jobobj[jobobj_id] = None
            elif "default" in inp:
                d = copy.copy(inp["default"])
                jobobj[jobobj_id] = d
            else:
                continue


        logging.info('{0}: Collected job object: \n {1}'.format(self.task_id, json.dumps(jobobj,indent=4)))

        valueFrom = {
            shortname(i["id"]).split("/")[-1]: i["valueFrom"] for i in self.cwl_step.tool["inputs"]
            if "valueFrom" in i}

        logging.info('{0}: Step inputs with valueFrom: \n{1}'.format(self.task_id, json.dumps(valueFrom,indent=4)))

        def postScatterEval(shortio):
            def valueFromFunc(k, v):
                if k in valueFrom:
                    return cwltool.workflow.expression.do_eval(
                        valueFrom[k], shortio, self.dag.requirements,
                        None, None, {}, context=v)
                else:
                    return v
            return {k: valueFromFunc(k, v) for k, v in shortio.items()}

        job = postScatterEval(jobobj)
        logging.info('{0}: Collected job object after valueFrom evaluation: \n {1}'.format(self.task_id, json.dumps(job,indent=4)))
        # maybe need to add here scatter functionality too

        kwargs = self.dag.default_args
        kwargs['outdir'] = tempfile.mkdtemp(prefix=os.path.join(self.outdir, "step_tmp"))
        kwargs['tmpdir_prefix']=kwargs['tmpdir_prefix'] if kwargs.get('tmpdir_prefix') else os.path.join(kwargs['outdir'], 'cwl_tmp_')
        kwargs['tmp_outdir_prefix']=kwargs['tmp_outdir_prefix'] if kwargs.get('tmp_outdir_prefix') else os.path.join(kwargs['outdir'], 'cwl_outdir_')

        output, status = cwltool.main.single_job_executor(self.cwl_step.embedded_tool,
                                                          job,
                                                          makeTool=cwltool.workflow.defaultMakeTool,
                                                          select_resources=None,
                                                          make_fs_access=cwltool.stdfsaccess.StdFsAccess,
                                                          **kwargs)
        if not output and status == "permanentFail":
            raise ValueError

        logging.info(
            '{0}: Embedded tool outputs: \n {1}'.format(self.task_id, json.dumps(output,indent=4)))

        promises = {}
        for out in self.cwl_step.tool["outputs"]:
            out_id = shortname(out["id"])
            jobout_id = out_id.split("/")[-1]
            try:
                promises[out_id] = output[jobout_id]
            except:
                continue

        data = {}
        data["promises"] = promises
        data["outdir"] = self.outdir

        logging.info(
            '{0}: Output: \n {1}'.format(self.task_id, json.dumps(data,indent=4)))

        return data
