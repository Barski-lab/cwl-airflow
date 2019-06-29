import logging
import os
import io
import sys
from tempfile import mkdtemp
from json import dumps

import schema_salad.schema
from schema_salad.ref_resolver import Loader, file_uri
import ruamel.yaml as yaml

from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from ..cwlutils import load_cwl
from cwl_airflow.utils.notifier import task_on_success, task_on_failure, task_on_retry, post_status
from cwl_airflow.utils.helpers import get_folder
from cwltool.main import jobloaderctx, init_job_order

_logger = logging.getLogger(__name__)


class CWLJobDispatcher(BaseOperator):

    ui_color = '#1E88E5'
    ui_fgcolor = '#FFF'

    @apply_defaults
    def __init__(
            self,
            task_id=None,
            ui_color=None,
            tmp_folder=None,
            *args, **kwargs):
        task_id = task_id if task_id else self.__class__.__name__

        kwargs.update({"on_success_callback": kwargs.get("on_success_callback", task_on_success),
                       "on_failure_callback": kwargs.get("on_failure_callback", task_on_failure),
                       "on_retry_callback":   kwargs.get("on_retry_callback",   task_on_retry)})

        super(CWLJobDispatcher, self).__init__(task_id=task_id, *args, **kwargs)

        self.tmp_folder = tmp_folder if tmp_folder else self.dag.default_args['tmp_folder']
        if ui_color: self.ui_color = ui_color

    def cwl_dispatch(self, json):
        try:
            cwlwf, it_is_workflow = load_cwl(self.dag.default_args["cwl_workflow"], self.dag.default_args)
            cwl_context = {"outdir": mkdtemp(dir=get_folder(os.path.abspath(self.tmp_folder)), prefix="dag_tmp_")}

            _jobloaderctx = jobloaderctx.copy()
            _jobloaderctx.update(cwlwf.metadata.get("$namespaces", {}))
            loader = Loader(_jobloaderctx)

            try:
                job_order_object = yaml.round_trip_load(io.StringIO(initial_value=dumps(json)))
                job_order_object, _ = loader.resolve_all(job_order_object,
                                                         file_uri(os.getcwd()) + "/",
                                                         checklinks=False)
            except Exception as e:
                _logger.error("Job Loader: {}".format(str(e)))

            job_order_object = init_job_order(job_order_object, None, cwlwf, loader, sys.stdout)

            cwl_context['promises'] = job_order_object

            logging.info(
                '{0}: Final job: \n {1}'.format(self.task_id, dumps(cwl_context, indent=4)))

            return cwl_context

        except Exception as e:
            _logger.info(
                'Dispatch Exception {0}: \n {1} {2}'.format(self.task_id, type(e), e))
            pass
        return None

    def execute(self, context):

        post_status(context)

        _json = {}

        if 'job' in context['dag_run'].conf:
            logging.debug(
                '{0}: dag_run conf: \n {1}'.format(self.task_id, context['dag_run'].conf['job']))
            _json = context['dag_run'].conf['job']

        cwl_context = self.cwl_dispatch(_json)
        if cwl_context:
            return cwl_context
        else:
            raise Exception("No cwl context")

