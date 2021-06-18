#! /usr/bin/env python3
import os

from copy import deepcopy
from airflow.models import DAG
from airflow.utils.dates import days_ago

from cwl_airflow.utilities.wdl import (
    fast_wdl_load,
    get_items,
    get_default_wdl_args
)
from cwl_airflow.extensions.operators.wdlstepoperator import WDLStepOperator
from cwl_airflow.extensions.operators.wdljobdispatcher import WDLJobDispatcher
from cwl_airflow.extensions.operators.wdljobgatherer import WDLJobGatherer
from cwl_airflow.utilities.report import (
    dag_on_success,
    dag_on_failure,
    task_on_success,
    task_on_failure,
    task_on_retry
)

from pprint import pprint
import itertools


class WDLDAG(DAG):

    def __init__(
        self,
        dag_id,          # the id of the DAG
        workflow,        # absolute path to the CWL workflow file or utf-8 string to include base64 encoded gzip compressed utf-8 workflow file content
        dispatcher=None,  # custom job dispatcher. Will be assigned automatically to the same DAG. Default CWLJobDispatcher
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


        self.workflow_tool = fast_wdl_load(         # keeps only the tool (CommentedMap object)
            workflow=self.workflow,
            # in case user has overwritten some of the default parameters
            wdl_args=kwargs["default_args"]["wdl"]
        )


       
        print('before attaching job dispatcher')
        self.dispatcher = WDLJobDispatcher(
            # need dag=self otherwise new operator will not get proper default_args
            dag=self,
            task_id="WDLJobDispatcher"
        ) if dispatcher is None else dispatcher

        print('before attaching job gatherer')
        self.gatherer = WDLJobGatherer(
            # need dag=self otherwise new operator will not get proper default_args
            dag=self,
            task_id="WDLJobGatherer"
        ) if gatherer is None else gatherer

        self.__assemble()

    def __setup_params(self, kwargs):
        """
        Updates kwargs with default values if those were not
        explicitely set on WDLDAG creation. "start_date" is set
        to days_ago(180) assuming that DAG run is not supposed
        to be queued longer then half a year:)
        """

        # default args provided by user. Use deepcopy to prevent from changing in place
        user_default_args = deepcopy(kwargs.get("default_args", {}))

        # get all the parameters required by cwltool with preset by user defaults
        required_wdl_args = get_default_wdl_args(
            preset_wdl_args=user_default_args.get("wdl", {})
        )

        # update default args provided by user with required by wdltool args
        user_default_args.update({
            "wdl": required_wdl_args
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

        # Updated default arguments required by CWL-Airflow with those that are provided by user for wdltool
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
        
        for task in self.workflow_tool.workflow.body:
            task_by_id[task.name] = WDLStepOperator(dag=self, task_id=task.name)
            for output in task.callee.outputs:
                out_id = output.name
                task_by_out_id[out_id] = task_by_id[task.name]
            for upstreams in task._memo_workflow_node_dependencies:
                upstreams = upstreams.split('-',1)
                try:
                    task_by_id[task.name].set_upstream(task_by_id[upstreams[1]])
                except KeyError:
                    task_by_id[task.name].set_upstream(self.dispatcher)


        for wf_outputs in self.workflow_tool.workflow.outputs:
            try:
                self.gatherer.set_upstream(task_by_out_id[wf_outputs.name])
            except KeyError:
                self.gatherer.set_upstream(self.dispatcher)

        if not self.gatherer.upstream_list:
            self.gatherer.set_upstream([task for task in task_by_id.values() if not task.downstream_list])

        if not self.dispatcher.downstream_list:
            self.dispatcher.set_downstream([task for task in task_by_id.values() if not task.upstream_list])





