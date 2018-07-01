import os
from airflow.models import DAG
from cwl_airflow.dag_components.cwlstepoperator import CWLStepOperator
from cwl_airflow.utils.utils import (shortname, flatten, load_cwl, convert_to_workflow)
from cwl_airflow.dag_components.jobdispatcher import JobDispatcher
from cwl_airflow.dag_components.jobcleanup import JobCleanup


class CWLDAG(DAG):

    @property
    def filepath(self):
        """
        Overwritten: File location of where the dag object is instantiated
        """
        return self.full_filepath

    def __init__(self, dag_id, default_args, *args, **kwargs):
        super(self.__class__, self).__init__(dag_id=dag_id, default_args=default_args, *args, **kwargs)
        self.cwlwf = load_cwl(default_args["job_data"]["content"]["workflow"])
        if self.cwlwf.tool["class"] == "CommandLineTool" or self.cwlwf.tool["class"] == "ExpressionTool":
            # workflow_file = os.path.join(default_args["tmp_folder"], os.path.basename(default_args["job_data"]["content"]["workflow"]))

            tool_dirname = os.path.dirname(default_args["job_data"]["content"]["workflow"])
            tool_filename, tool_ext = os.path.splitext(os.path.basename(default_args["job_data"]["content"]["workflow"]))
            workflow_file = os.path.join(tool_dirname, tool_filename + '_workflow' + tool_ext)

            self.cwlwf = load_cwl(convert_to_workflow(tool=self.cwlwf.tool,
                                                      tool_file=default_args["job_data"]["content"]["workflow"],
                                                      workflow_file=workflow_file))
        self.requirements = self.cwlwf.tool.get("requirements", [])

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
            if isinstance(current_task, JobCleanup):
                continue
            if isinstance(current_task, JobDispatcher):
                current_task_outputs_id = [shortname(current_task_output["id"]) for current_task_output in current_task.dag.cwlwf.tool["inputs"]]
            else:
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
