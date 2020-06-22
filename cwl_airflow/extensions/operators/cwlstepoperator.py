#! /usr/bin/env python3

import logging
import json
import os, sys, tempfile
import copy
import glob
import subprocess
import shutil

from jsonmerge import merge

from cwltool.stdfsaccess import StdFsAccess
from cwltool.workflow import expression
from cwltool.context import RuntimeContext, getdefault
from cwltool.pathmapper import visit_class
from cwltool.mutation import MutationManager

from cwl_airflow.utils.cwlutils import (
    flatten, 
    shortname, 
    load_cwl
)
from airflow.utils.log.logging_mixin import StreamLogWriter
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults

from cwl_airflow.utilities.cwl import (
    fast_cwl_step_load,
    get_items
)
from cwl_airflow.utils.report import post_status


class CWLStepOperator(BaseOperator):


    @apply_defaults  # in case someone decided to overwrite default_args from the DAG
    def __init__(
        self,
        task_id,
        *args, **kwargs
    ):
        super().__init__(task_id=task_id, *args, **kwargs)


    def execute(self, context):
        post_status(context)

        default_args = context["dag"].default_args
        workflow_step_tool = fast_cwl_step_load(default_args, task_id)





        step_outpus, step_status = SingleJobExecutor().execute(workflow_step_tool, job, runtime_context)



        upstream_task_ids = [t.task_id for t in self.upstream_list] + \
                            ([self.reader_task_id] if self.reader_task_id else [])

        upstream_data = self.xcom_pull(context=context, task_ids=upstream_task_ids)

        promises = {}
        for data in upstream_data:  # upstream_data is an array with { promises and outdir }
            promises = merge(promises, data["promises"])
            if "outdir" in data:
                self.outdir = data["outdir"]

        _d_args = self.dag.default_args

        if not self.outdir:
            self.outdir = _d_args['tmp_folder']

        jobobj = {}

        for inp in self.cwl_step.tool["inputs"]:
            jobobj_id = shortname(inp["id"]).split("/")[-1]
            source_ids = []
            promises_outputs = []
            try:
                source_field = inp["source"] if it_is_workflow else inp.get("id")
                source_ids = [shortname(s) for s in source_field] if isinstance(source_field, list) else [shortname(source_field)]
                promises_outputs = [promises[source_id] for source_id in source_ids if source_id in promises]
            except:
                _logger.warning("{0}: Couldn't find source field in step input: {1}"
                                .format(self.task_id,
                                        json.dumps(inp, indent=4)))

            _logger.info('{0}: For input {1} with source_ids: {2} found upstream outputs: \n{3}'
                         .format(self.task_id,
                                 jobobj_id,
                                 source_ids,
                                 promises_outputs))

            if len(promises_outputs) > 1:
                if inp.get("linkMerge", "merge_nested") == "merge_flattened":
                    jobobj[jobobj_id] = flatten(promises_outputs)
                else:
                    jobobj[jobobj_id] = promises_outputs
            # Should also check if [None], because in this case we need to take default value
            elif len(promises_outputs) == 1 and (promises_outputs[0] is not None):
                jobobj[jobobj_id] = promises_outputs[0]
            elif "valueFrom" in inp:
                jobobj[jobobj_id] = None
            elif "default" in inp:
                d = copy.copy(inp["default"])
                jobobj[jobobj_id] = d
            else:
                continue


        def _post_scatter_eval(shortio, cwl_step):
            _value_from = {
                shortname(i["id"]).split("/")[-1]:
                    i["valueFrom"] for i in cwl_step.tool["inputs"] if "valueFrom" in i
                }
            _logger.debug(
                '{0}: Step inputs with valueFrom: \n{1}'.format(self.task_id, json.dumps(_value_from, indent=4)))

            def value_from_func(k, v):
                if k in _value_from:
                    return expression.do_eval(
                        _value_from[k], shortio,
                        self.cwlwf.tool.get("requirements", []),
                        None, None, {}, context=v)
                else:
                    return v
            return {k: value_from_func(k, v) for k, v in shortio.items()}

        job = _post_scatter_eval(jobobj, self.cwl_step)
        _logger.info('{0}: Final job data: \n {1}'.format(self.task_id, json.dumps(job, indent=4)))

        _d_args['outdir'] = tempfile.mkdtemp(prefix=os.path.join(self.outdir, "step_tmp"))
        _d_args['tmpdir_prefix'] = os.path.join(_d_args['outdir'], 'cwl_tmp_')
        _d_args['tmp_outdir_prefix'] = os.path.join(_d_args['outdir'], 'cwl_outdir_')

        _d_args["record_container_id"] = True
        _d_args["cidfile_dir"] = _d_args['outdir']
        _d_args["cidfile_prefix"] = self.task_id


        executor = SingleJobExecutor()
        runtimeContext = RuntimeContext(_d_args)
        runtimeContext.make_fs_access = getdefault(runtimeContext.make_fs_access, StdFsAccess)

        for inp in self.cwl_step.tool["inputs"]:
            if inp.get("not_connected"):
                del job[shortname(inp["id"].split("/")[-1])]

        _stderr = sys.stderr
        sys.stderr = sys.__stderr__
        (output, status) = executor(self.cwl_step.embedded_tool if it_is_workflow else self.cwl_step,
                                    job,
                                    runtimeContext,
                                    logger=_logger)
        sys.stderr = _stderr

        if not output and status == "permanentFail":
            raise ValueError

        _logger.debug(
            '{0}: Embedded tool outputs: \n {1}'.format(self.task_id, json.dumps(output, indent=4)))

        promises = {}


        for out in self.cwl_step.tool["outputs"]:

            out_id = shortname(out["id"])
            jobout_id = out_id.split("/")[-1]
            try:
                promises[out_id] = output[jobout_id]
            except:
                continue

        # Unsetting the Generation from final output object
        visit_class(promises, ("File",), MutationManager().unset_generation)

        data = {"promises": promises, "outdir": self.outdir}

        _logger.info(
            '{0}: Output: \n {1}'.format(self.task_id, json.dumps(data, indent=4)))

        return data

    def on_kill(self):
        _logger.info("Stop docker containers")
        for cidfile in glob.glob(os.path.join(self.dag.default_args["cidfile_dir"], self.task_id + "*.cid")):  # make this better, doesn't look good to read from self.dag.default_args
            try:
                with open(cidfile, "r") as inp_stream:
                    _logger.debug(f"""Read container id from {cidfile}""")
                    command = ["docker", "kill", inp_stream.read()]
                    _logger.debug(f"""Call {" ".join(command)}""")
                    p = subprocess.Popen(command, shell=False)
                    try:
                        p.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        p.kill()
            except Exception as ex:
                _logger.error(f"""Failed to stop docker container with ID from {cidfile}\n {ex}""")

        # _logger.info(f"""Delete temporary output directory {self.outdir}""")
        # try:
        #     shutil.rmtree(self.outdir)
        # except Exception as ex:
        #     _logger.error(f"""Failed to delete temporary output directory {self.outdir}\n {ex}""")
