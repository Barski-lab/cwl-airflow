import logging
from airflow.models import BaseOperator
from airflow.utils import (apply_defaults)
import os
from cwltool.pathmapper import adjustDirObjs, visit_class, trim_listing
from cwltool.process import normalizeFilesDirs
from cwl_airflow.utils.utils import load_job
import json
from cwl_airflow.utils.utils import url_shortname
from six.moves import urllib


class JobDispatcher(BaseOperator):

    @apply_defaults
    def __init__(self,
                 job_file=None,
                 *args,
                 **kwargs):

        super(JobDispatcher, self).__init__(*args, **kwargs)
        self.job_file = job_file


    def execute(self, context):
        logging.info('{self.task_id}: Looking for file {self.job_file}'.format(**locals()))
        job_order_object = load_job(self.job_file)
        logging.info('{0}: Resolved job object from file: {1} \n{2}'.format(self.task_id, self.job_file, json.dumps(job_order_object, indent=4)))
        fragment = urllib.parse.urlsplit(self.dag.default_args["main_workflow"]).fragment
        fragment = fragment + '/' if fragment else ''
        job_order_object_extended = {fragment + key: value for key, value in job_order_object.items()}
        cwl_context = {}
        cwl_context['promises'] = job_order_object_extended
        logging.info(
            '{0}: Output: \n {1}'.format(self.task_id, json.dumps(cwl_context, indent=4)))
        return cwl_context
