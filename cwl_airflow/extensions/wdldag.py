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

        print('before loading wdl file')

        self.workflow_tool = fast_wdl_load(         # keeps only the tool (CommentedMap object)
            workflow=self.workflow,
            # in case user has overwritten some of the default parameters
            wdl_args=kwargs["default_args"]["wdl"]
        )

        print('after loading wdl file')
        #print(self.workflow_tool)
        pprint(vars(self.workflow_tool))

       
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

        print('before calling assemble')
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

        #pprint(vars(self.workflow_tool.workflow))

        print("_body:")
        print(self.workflow_tool.workflow.body)
        for call in self.workflow_tool.workflow.body:
            #pprint(vars(call))
            print('_call:')
            print(call.name)
            task_by_id[call.name] = call.name
            task_by_out_id[call.name] = call.callee.outputs
            print('checking attrs')
            pprint(vars(call))
            print('callee')
            pprint(vars(call.callee))
            print('callee.command')
            pprint((vars(call.callee.command)))
            print(list(call._after_node_ids))
            for nodes in call._after_node_ids:
                print('nodes')
                print(nodes.expr)
            # print(list(call.children))
            # print('dependencies')
            # print(call._memo_workflow_node_dependencies)
            
            for child in call.children:
                print('_call.children:')
                print(child.expr, child.member)
                #print(list(child.children))
                for grandchild in child.children:
                    print('_child.children:')
                    print(grandchild.name)
                    print(list(grandchild.children))

        print('task by id')
        print(task_by_id)

        print('task by out id')
        print(task_by_out_id)
        # for task in self.workflow_tool.tasks:
        #     print(task.name)
        #     pprint(vars(task))
            
            
            #pprint(vars(task.parent))
            
            # task_by_id[step_id] = WDLStepOperator(dag=self, task_id=step_id)
            # for step_out_id, _ in get_items(step_data["out"]):
            #     task_by_out_id[step_out_id] = task_by_id[step_id]

        # for step_id, step_data in get_items(self.workflow_tool.tasks):
        #     # step might not have "in"
        #     for step_in_id, step_in_data in get_items(step_data.get("in", [])):
        #         # "in" might not have "source"
        #         for step_in_source, _ in get_items(step_in_data.get("source", [])):
        #             try:
        #                 task_by_id[step_id].set_upstream(
        #                     task_by_out_id[step_in_source])  # connected to another step
        #             except KeyError:
        #                 # connected to dispatcher
        #                 task_by_id[step_id].set_upstream(self.dispatcher)
        #     # safety measure in case "in" was empty
        #     if not step_data.get("in", []):
        #         # connected to dispatcher
        #         task_by_id[step_id].set_upstream(self.dispatcher)

        # for _, output_data in get_items(self.workflow_tool["outputs"]):
        #     # in case "outputSource" is a list
        #     for output_source_id, _ in get_items(output_data["outputSource"]):
        #         try:
        #             # connected to another step
        #             self.gatherer.set_upstream(
        #                 task_by_out_id[output_source_id])
        #         except KeyError:
        #             # connected to dispatcher
        #             self.gatherer.set_upstream(self.dispatcher)

        # # safety measure in case of very specific workflows
        # # if gatherer happened to be not connected to anything, connect it to all "leaves"
        # # if dispatcher happened to be not connected to anything, connect it to all "roots"

        # if not self.gatherer.upstream_list:
        #     self.gatherer.set_upstream(
        #         [task for task in task_by_id.values() if not task.downstream_list])

        # if not self.dispatcher.downstream_list:
        #     self.dispatcher.set_downstream(
        #         [task for task in task_by_id.values() if not task.upstream_list])


