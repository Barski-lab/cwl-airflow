import sys
import os
import json
import copy
import logging
import tempfile
from airflow.models import BaseOperator
from jsonmerge import merge
import cwltool.executors
import cwltool.workflow
import cwltool.errors
import cwltool.stdfsaccess
from cwltool.context import RuntimeContext, getdefault
from cwl_airflow.utils.utils import (shortname, flatten)
from airflow.utils.log.logging_mixin import StreamLogWriter


class StreamLogWriterUpdated (StreamLogWriter):

    def fileno(self):
        return -1


class CWLStepOperator(BaseOperator):

    def __init__(self, cwl_step, *args, **kwargs):
        self.cwl_step = cwl_step
        super(self.__class__, self).__init__(task_id=shortname(cwl_step.tool["id"]).split("/")[-1], *args, **kwargs)

    def execute(self, context):
        logging.info('Running tool: \n{}'.format(json.dumps(self.cwl_step.tool, indent=4)))
        collected_outputs = {}
        for task_outputs in self.xcom_pull(context=context, task_ids=[task.task_id for task in self.upstream_list]):
            collected_outputs = merge(collected_outputs, task_outputs["outputs"])
        logging.debug('Collected outputs:\n{}'.format(json.dumps(collected_outputs, indent=4)))

        jobobj = {}

        for inp in self.cwl_step.tool["inputs"]:
            jobobj_id = shortname(inp["id"]).split("/")[-1]
            source_ids = []
            promises_outputs = []
            try:
                source_ids = [shortname(source) for source in inp["source"]] if isinstance(inp["source"], list) else [shortname(inp["source"])]
                promises_outputs = [collected_outputs[source_id] for source_id in source_ids if source_id in collected_outputs]
            except Exception as ex:
                logging.info("{0}: Couldn't find source field in step input:\n{1}".format(self.task_id,json.dumps(inp,indent=4)))
            logging.info('For input {} with source_ids: {} found upstream outputs: \n{}'.format(jobobj_id, source_ids, promises_outputs))
            if len(promises_outputs) > 1:
                if inp.get("linkMerge", "merge_nested") == "merge_flattened":
                    jobobj[jobobj_id] = flatten(promises_outputs)
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
        tmp_folder = collected_outputs["tmp_folder"]
        output_folder = collected_outputs["output_folder"]
        kwargs['outdir'] = tempfile.mkdtemp(dir=tmp_folder, prefix="step_tmp_")
        kwargs['tmpdir_prefix'] = os.path.join(tmp_folder, "cwl_tmp_")
        kwargs['tmp_outdir_prefix'] = os.path.join(tmp_folder, "cwl_outdir_tmp_")
        kwargs['rm_tmpdir'] = False
        kwargs["basedir"] = os.path.abspath(os.path.dirname(self.dag.default_args["job_data"]["path"]))

        logger = logging.getLogger("cwltool")
        sys.stdout = StreamLogWriterUpdated(logger, logging.INFO)
        sys.stderr = StreamLogWriterUpdated(logger, logging.WARN)

        executor = cwltool.executors.SingleJobExecutor()
        runtimeContext = RuntimeContext(kwargs)
        runtimeContext.make_fs_access = getdefault(runtimeContext.make_fs_access, cwltool.stdfsaccess.StdFsAccess)

        for inp in self.cwl_step.tool["inputs"]:
            if inp.get("not_connected"):
                del job[shortname(inp["id"].split("/")[-1])]

        (output, status) = executor(self.cwl_step.embedded_tool,
                                    job,
                                    runtimeContext,
                                    logger=logger)

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

        promises["tmp_folder"] = tmp_folder
        promises["output_folder"] = output_folder
        data = {"outputs": promises}

        logging.info(
            '{0}: Output: \n {1}'.format(self.task_id, json.dumps(data, indent=4)))

        return data
