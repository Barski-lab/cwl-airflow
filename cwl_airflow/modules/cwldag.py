#
# CWLDAG creates airfow DAG where each step is CWLStepOperator
#  to assign steps upfront of CWL
#

import cwltool.main
import cwltool.load_tool
import cwltool.workflow
import cwltool.errors
from cwltool.resolver import tool_resolver
from airflow.models import DAG
from cwl_airflow.modules.cwlstepoperator import CWLStepOperator
from cwl_airflow.modules.cwlutils import shortname, flatten
import os
from cwl_airflow.modules.jobdispatcher import JobDispatcher
from cwl_airflow.modules.jobcleanup import JobCleanup
import json
from six.moves import urllib


def check_unsupported_feature (tool):
    if tool["class"] == "Workflow" and [step["id"] for step in tool["steps"] if "scatter" in step]:
        return True, "Scatter is not supported"
    return False, None

class CWLDAG(DAG):

    @property
    def filepath(self):
        """
        Overwritten: File location of where the dag object is instantiated
        """
        return self.full_filepath

    def __init__(
            self,
            dag_id=None,
            default_args=None,
            *args, **kwargs):

        _dag_id = dag_id if dag_id else urllib.parse.urldefrag(default_args["cwl_workflow"])[0].split("/")[-1].replace(".cwl", "").replace(".", "_dot_")
        super(self.__class__, self).__init__(dag_id=_dag_id,
                                             default_args=default_args, *args, **kwargs)

        self.cwlwf = cwltool.load_tool.load_tool(argsworkflow = default_args["cwl_workflow"],
                                                 makeTool = cwltool.workflow.defaultMakeTool,
                                                 resolver = tool_resolver,
                                                 strict = default_args['strict'])

        if type(self.cwlwf) == int or check_unsupported_feature(self.cwlwf.tool)[0]:
            raise cwltool.errors.UnsupportedRequirement(check_unsupported_feature(self.cwlwf.tool)[1])

        if self.cwlwf.tool["class"] == "CommandLineTool" or self.cwlwf.tool["class"] == "ExpressionTool":
            dirname = os.path.dirname(default_args["cwl_workflow"])
            filename, ext = os.path.splitext(os.path.basename(default_args["cwl_workflow"]))
            new_workflow_name = os.path.join(dirname, filename + '_workflow' + ext)
            generated_workflow = self.gen_workflow (self.cwlwf.tool, default_args["cwl_workflow"])
            with open(new_workflow_name, 'w') as generated_workflow_stream:
                generated_workflow_stream.write(json.dumps(generated_workflow, indent=4))
            self.cwlwf = cwltool.load_tool.load_tool(argsworkflow = new_workflow_name,
                                                     makeTool = cwltool.workflow.defaultMakeTool,
                                                     resolver=tool_resolver,
                                                     strict = default_args['strict'])

        self.requirements = self.cwlwf.tool.get("requirements", [])


    def gen_workflow_inputs(self, cwl_tool):
        inputs = []
        for input in cwl_tool["inputs"]:
            custom_input = {}
            if input.get("id", None): custom_input["id"] = shortname(input["id"])
            if input.get("type", None): custom_input["type"] = input["type"]
            if input.get("format", None): custom_input["format"] = input["format"]
            if input.get("doc", None): custom_input["doc"] = input["doc"]
            if input.get("label", None): custom_input["label"] = input["label"]
            inputs.append(custom_input)
        return inputs


    def gen_workflow_outputs(self, cwl_tool):
        outputs = []
        for output in cwl_tool["outputs"]:
            custom_output = {}
            if output.get("id", None): custom_output["id"] = shortname(output["id"])
            if output.get("type", None): custom_output["type"] = output["type"]
            if output.get("format", None): custom_output["format"] = output["format"]
            if output.get("doc", None): custom_output["doc"] = output["doc"]
            if output.get("label", None): custom_output["label"] = output["label"]
            if output.get("id", None): custom_output["outputSource"] = "static_step/" + shortname(output["id"])
            outputs.append(custom_output)
        return outputs


    def gen_workflow_steps(self, cwl_file, workflow_inputs, workflow_outputs):
        steps = []
        steps.append ({ \
                        "run": cwl_file, \
                        "in": [{"source": workflow_input["id"], "id": workflow_input["id"]} for workflow_input in workflow_inputs], \
                        "out": [output["id"] for output in workflow_outputs], \
                        "id": "static_step" \
                      })
        return steps

    def gen_workflow(self, cwl_tool, cwl_file):
        a_workflow = {}
        a_workflow["cwlVersion"] = "v1.0"
        a_workflow["class"] = "Workflow"
        a_workflow["inputs"] = self.gen_workflow_inputs(cwl_tool)
        a_workflow["outputs"] = self.gen_workflow_outputs(cwl_tool)
        a_workflow["steps"] = self.gen_workflow_steps(cwl_file, a_workflow["inputs"], a_workflow["outputs"])
        if cwl_tool.get("$namespaces", None): a_workflow["$namespaces"] = cwl_tool["$namespaces"]
        if cwl_tool.get("$schemas", None): a_workflow["$schemas"] = cwl_tool["$schemas"]
        if cwl_tool.get("requirements", None): a_workflow["requirements"] = cwl_tool["requirements"]
        return a_workflow


    def create(self):
        outputs = {}
        for step in self.cwlwf.steps:
            cwl_task = CWLStepOperator(cwl_step=step, dag=self)
            outputs[shortname(step.tool["id"])] = cwl_task
            for out in step.tool["outputs"]:
                outputs[shortname(out["id"])] = cwl_task
        for step in self.cwlwf.steps:
            current_task = outputs[shortname(step.tool["id"])]
            for inp in step.tool["inputs"]:
                step_input_sources = inp.get("source", '') if isinstance(inp.get("source", ''), list) else [inp.get("source", '')]
                for source in step_input_sources:
                    parent_task = outputs.get(shortname(source), None)
                    if parent_task and parent_task not in current_task.upstream_list:
                        current_task.set_upstream(parent_task)

    def assign_job_dispatcher(self, task):
        for current_task in self.tasks:
            if isinstance(current_task, JobDispatcher) or isinstance(current_task, JobCleanup):
                continue
            current_task_input_sources = [shortname(source) for source in flatten([current_task_input["source"] \
                                                                                   for current_task_input in current_task.cwl_step.tool["inputs"] \
                                                                                   if "source" in current_task_input])]
            workflow_input_id = [shortname(workflow_input["id"]) for workflow_input in self.cwlwf.tool["inputs"]]
            # Should also check if current_task is on top, 'cos if task has all parameters to be set by
            # default and don't need any of its inputs to be read from the file
            # but it suppose to either return something directly to workflow output
            # or through the other tasks which don't have connections with JobDispatcher too,
            # it may happen that it will lost 'outdir', because the last one is set only by JoDispatcher task
            if any(i in current_task_input_sources for i in workflow_input_id) or not current_task.upstream_list:
                current_task.set_upstream(task)

    def assign_job_cleanup(self, task):
        for current_task in self.tasks:
            if isinstance(current_task, JobDispatcher) or isinstance(current_task, JobCleanup):
                continue
            current_task_outputs_id = [shortname(current_task_output["id"]) for current_task_output in current_task.cwl_step.tool["outputs"]]
            workflow_outputs_outputsource = [shortname(workflow_output["outputSource"]) for workflow_output in self.cwlwf.tool["outputs"]]
            # print "current_task_outputs_id: \n", yaml.round_trip_dump(current_task_outputs_id)
            # print "workflow_outputs_outputsource: \n", yaml.round_trip_dump(workflow_outputs_outputsource)
            if any(i in current_task_outputs_id for i in workflow_outputs_outputsource):
                task.set_upstream(current_task)

    def get_output_list(self):
        # return [shortname(o) for o in self.cwlwf.tool["outputs"] ]
        outputs = {}
        for out in self.cwlwf.tool["outputs"]:
            outputs[shortname(out["outputSource"])] = shortname(out["id"])
        return outputs
