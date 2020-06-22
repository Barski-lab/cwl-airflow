import logging
import os
import io
import sys
import schema_salad.schema
import ruamel.yaml as yaml

from tempfile import mkdtemp
from json import dumps
from schema_salad.ref_resolver import Loader, file_uri
from cwltool.main import jobloaderctx, init_job_order

from cwl_airflow.utils.cwlutils import load_cwl
from cwl_airflow.utils.notifier import (
    task_on_success,
    task_on_failure,
    task_on_retry,
    post_status
)
from cwl_airflow.utils.helpers import get_folder, CleanAirflowImport

from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults




class CWLJobDispatcher(BaseOperator):


    @apply_defaults  # in case someone decided to overwrite default_args from the DAG
    def __init__(
            self,
            task_id,
            *args, **kwargs
    ):
        super().__init__(task_id=task_id, *args, **kwargs)


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

        default_args = context["dag"].default_args

        job = {}

        if "job" in context["dag_run"].conf:
            job = context["dag_run"].conf["job"]

        cwl_context = self.cwl_dispatch(_json)
        if cwl_context:
            return cwl_context
        else:
            raise Exception("No cwl context")

