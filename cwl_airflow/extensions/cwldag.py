#! /usr/bin/env python3
import os

from copy import deepcopy
from airflow.models import DAG
from airflow.utils.dates import days_ago

from cwl_airflow.utilities.cwl import (
    fast_cwl_load,
    get_items,
    get_default_cwl_args
)
from cwl_airflow.extensions.operators.cwlstepoperator import CWLStepOperator
from cwl_airflow.extensions.operators.cwljobdispatcher import CWLJobDispatcher
from cwl_airflow.extensions.operators.cwljobgatherer import CWLJobGatherer
from cwl_airflow.utilities.report import (
    dag_on_success,
    dag_on_failure,
    task_on_success,
    task_on_failure,
    task_on_retry
)


class CWLDAG(DAG):

    def __init__(
        self,
        dag_id,          # the id of the DAG
        workflow,        # absolute path to the CWL workflow file or utf-8 string to include base64 encoded zlib compressed utf-8 workflow file content
        dispatcher=None, # custom job dispatcher. Will be assigned automatically to the same DAG. Default CWLJobDispatcher
        gatherer=None,   # custom job gatherer. Will be assigned automatically to the same DAG. Default CWLJobGatherer
        *args, **kwargs  # see DAG class for additional parameters
    ):
        """
        Updates kwargs with the required defaults if they were not explicitely provided
        by user. dispatcher and gatherer are set to CWLJobDispatcher() and CWLJobGatherer()
        if those were not provided by user. If user sets his own operators for dispatcher
        and gatherer, "default_args" will not be inherited. User needs to set up proper
        agruments by himself. Also, dag results will not be posted from the custom dispatcher.
        """

        self.workflow = workflow
        self.__setup_params(kwargs)

        super().__init__(dag_id=dag_id, *args, **kwargs)

        self.workflow_tool = fast_cwl_load(         # keeps only the tool (CommentedMap object)
            workflow=self.workflow,
            cwl_args=kwargs["default_args"]["cwl"]  # in case user has overwritten some of the default parameters
        )

        self.dispatcher = CWLJobDispatcher(
            dag=self,                               # need dag=self otherwise new operator will not get proper default_args
            task_id="CWLJobDispatcher"
        ) if dispatcher is None else dispatcher

        self.gatherer = CWLJobGatherer(
            dag=self,                               # need dag=self otherwise new operator will not get proper default_args
            task_id="CWLJobGatherer"
        ) if gatherer is None else gatherer

        self.__assemble()


    def __setup_params(self, kwargs):
        """
        Updates kwargs with default values if those were not
        explicitely set on CWLDAG creation. "start_date" is set
        to days_ago(180) assuming that DAG run is not supposed
        to be queued longer then half a year:)
        """

        # default args provided by user. Use deepcopy to prevent from changing in place
        user_default_args = deepcopy(kwargs.get("default_args", {}))
        
        # get all the parameters required by cwltool with preset by user defaults
        required_cwl_args = get_default_cwl_args(
            preset_cwl_args=user_default_args.get("cwl", {})
        )

        # update default args provided by user with required by cwltool args
        user_default_args.update({
            "cwl": required_cwl_args
        })

        # default arguments required by CWL-Airflow (no need to put it in a separate function so far)
        required_default_args = {
            "start_date": days_ago(180),
            "email_on_failure": False,
            "email_on_retry": False,
            "on_failure_callback": task_on_failure,
            "on_success_callback": task_on_success,
            "on_retry_callback": task_on_retry
        }
        
        # Updated default arguments required by CWL-Airflow with those that are provided by user for cwltool
        required_default_args.update(user_default_args)

        # update kwargs with correct default_args and callbacks if those were not set by user
        kwargs.update(
            {
                "default_args": required_default_args,
                "on_failure_callback": kwargs.get("on_failure_callback", dag_on_failure),
                "on_success_callback": kwargs.get("on_success_callback", dag_on_success),
                "schedule_interval": None
            }
        )


    def __assemble(self):
        """
        Creates DAG based on the parsed CWL workflow structure.
        Assignes dispatcher and gatherer tasks
        """

        # TODO: add support for CommandLineTool and ExpressionTool
        # TODO: add colors for Tasks?

        task_by_id = {}         # to get airflow task assosiated with workflow step by its id
        task_by_out_id = {}     # to get airflow task assosiated with workflow step by its out id
        
        for step_id, step_data in get_items(self.workflow_tool["steps"]):
            task_by_id[step_id] = CWLStepOperator(dag=self, task_id=step_id)
            for step_out_id, _ in get_items(step_data["out"]):
                task_by_out_id[step_out_id] = task_by_id[step_id]

        for step_id, step_data in get_items(self.workflow_tool["steps"]):
            for step_in_id, step_in_data in get_items(step_data.get("in", [])):           # step might not have "in"
                for step_in_source, _ in get_items(step_in_data.get("source", [])):       # "in" might not have "source"
                    try:
                        task_by_id[step_id].set_upstream(task_by_out_id[step_in_source])  # connected to another step
                    except KeyError:
                        task_by_id[step_id].set_upstream(self.dispatcher)                 # connected to dispatcher
            if not step_data.get("in", []):                                               # safety measure in case "in" was empty
                task_by_id[step_id].set_upstream(self.dispatcher)                         # connected to dispatcher


        for _, output_data in get_items(self.workflow_tool["outputs"]):
            for output_source_id, _ in get_items(output_data["outputSource"]):            # in case "outputSource" is a list
                try:
                    self.gatherer.set_upstream(task_by_out_id[output_source_id])          # connected to another step
                except KeyError:
                    self.gatherer.set_upstream(self.dispatcher)                           # connected to dispatcher

        # safety measure in case of very specific workflows
        # if gatherer happened to be not connected to anything, connect it to all "leaves"
        # if dispatcher happened to be not connected to anything, connect it to all "roots"

        if not self.gatherer.upstream_list:
            self.gatherer.set_upstream([task for task in task_by_id.values() if not task.downstream_list])

        if not self.dispatcher.downstream_list:
            self.dispatcher.set_downstream([task for task in task_by_id.values() if not task.upstream_list])
