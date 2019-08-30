#! /usr/bin/env python3

import logging
import json
from ruamel import yaml
from six.moves import urllib
from cwltool.argparser import get_default_args
from airflow.models import DAG
from airflow.operators import BaseOperator
from airflow.exceptions import AirflowException
from airflow.utils.dates import days_ago
from .cwlstepoperator import CWLStepOperator
from .cwlutils import conf_get_default
from cwl_airflow.utils.notifier import dag_on_success, dag_on_failure
# logging.getLogger('cwltool').setLevel(conf_get_default('core', 'logging_level', 'ERROR').upper())
# logging.getLogger('salad').setLevel(conf_get_default('core', 'logging_level', 'ERROR').upper())
logging.getLogger('cwltool').setLevel(logging.ERROR)
logging.getLogger('past.translation').setLevel(logging.ERROR)
logging.getLogger('salad').setLevel(logging.ERROR)
logging.getLogger('rdflib').setLevel(logging.ERROR)

_logger = logging.getLogger(__name__)
_logger.setLevel(conf_get_default('core', 'logging_level', 'ERROR').upper())


class CWLDAG(DAG):

    def __init__(
            self,
            dag_id=None,
            cwl_workflow=None,
            default_args={},
            schedule_interval=None,
            *args, **kwargs):

        self.top_task = None
        self.bottom_task = None
        self.cwlwf = self.quick_load_cwl(cwl_workflow)

        kwargs.update({"on_failure_callback": kwargs.get("on_failure_callback", dag_on_failure),
                       "on_success_callback": kwargs.get("on_success_callback", dag_on_success)})

        init_default_args = {
            'start_date': days_ago(14),
            'email_on_failure': False,
            'email_on_retry': False,
            'end_date': None,
            'tmp_folder': conf_get_default('cwl', 'tmp_folder', '/tmp'),
            'basedir': conf_get_default('cwl', 'tmp_folder', '/tmp'),
            'no_match_user': conf_get_default('cwl', 'no_match_user', False),
            'task_retries': conf_get_default('cwl', 'retry', 1),
            'quiet': False,
            'strict': False,
            'on_error': 'continue',
            'skip_schemas': True,
            'cwl_workflow': cwl_workflow
        }

        init_default_args.update(default_args)
        merged_default_args = get_default_args()
        merged_default_args.update(init_default_args)

        super(self.__class__, self).__init__(dag_id=dag_id if dag_id else urllib.parse.urldefrag(cwl_workflow)[0].split("/")[-1].replace(".cwl", "").replace(".", "_dot_"),
                                             default_args=merged_default_args,
                                             schedule_interval=schedule_interval, *args, **kwargs)

    def quick_load_cwl(self, cwl_file):
        with open(cwl_file, "r") as input_stream:
            cwl_data = yaml.round_trip_load(input_stream, preserve_quotes=True)
        return cwl_data

    def create(self):
        if self.cwlwf["class"] in ["CommandLineTool", "ExpressionTool"]:
            cwl_task = CWLStepOperator(task_id=self.dag_id,
                                       dag=self,
                                       retries=self.default_args["task_retries"],
                                       ui_color='#5C6BC0')
        else:
            outputs = {}

            for step_id, step_val in self.cwlwf["steps"].items():
                cwl_task = CWLStepOperator(task_id=step_id,
                                           dag=self,
                                           retries=self.default_args["task_retries"],
                                           ui_color='#5C6BC0')
                outputs[step_id] = cwl_task

                for out in step_val["out"]:
                    outputs["/".join([step_id, out])] = cwl_task

            for step_id, step_val in self.cwlwf["steps"].items():
                current_task = outputs[step_id]
                if not step_val["in"]:  # need to check it, because in can be set as []
                    continue
                for inp_id, inp_val in step_val["in"].items():
                    if isinstance(inp_val, list):
                        step_input_sources = inp_val
                    elif isinstance(inp_val, str):
                        step_input_sources = [inp_val]
                    elif isinstance(inp_val, dict) and "source" in inp_val:
                        if isinstance(inp_val["source"], list):
                            step_input_sources = inp_val["source"]
                        else:
                            step_input_sources = [inp_val["source"]]
                    else:
                        step_input_sources = []

                    for source in step_input_sources:
                        parent_task = outputs.get(source, None)
                        if parent_task and parent_task not in current_task.upstream_list:
                            current_task.set_upstream(parent_task)

        # https://material.io/guidelines/style/color.html#color-color-palette
        for t in self.tasks:
            if not t.downstream_list and t.upstream_list:
                t.ui_color = '#4527A0'
            elif not t.upstream_list:
                t.ui_color = '#303F9F'

    def add(self, task, to=None):
        if not isinstance(task, BaseOperator):
            raise AirflowException(
                "Relationships can only be set between "
                "Operators; received {}".format(task.__class__.__name__))
        if to == 'top':
            self.top_task = self.top_task if self.top_task else task
            task.set_downstream([t for t in self.tasks if t.task_id != task.task_id and not t.upstream_list])
        elif to == 'bottom':
            self.bottom_task = self.bottom_task if self.bottom_task else task
            task.set_upstream([t for t in self.tasks if t.task_id != task.task_id and not t.downstream_list])

        if self.top_task and self.bottom_task:
            self.bottom_task.reader_task_id = self.top_task.task_id
            for t in self.tasks:
                if t.task_id != self.top_task.task_id:
                    t.reader_task_id = self.top_task.task_id

    def get_output_list(self):
        outputs = {}
        for out_id, out_val in self.cwlwf["outputs"].items():
            if "outputSource" in out_val:
                outputs[out_val["outputSource"]] = out_id
            else:
                outputs[out_id] = out_id
        _logger.debug("{0} get_output_list: \n{1}".format(self.dag_id, outputs))
        return outputs
