import logging
import connexion
import random
import string
import json
import tempfile
import psutil
import shutil

import cwltool.load_tool as load  # TODO: use my functions instead
from schema_salad.ref_resolver import Loader

from time import sleep
from werkzeug.utils import secure_filename
from six import iterlists
from os import path

from airflow.settings import DAGS_FOLDER, AIRFLOW_HOME
from airflow.models import DagBag, TaskInstance, DagRun, DagModel
from airflow.utils.state import State
from airflow.utils.timezone import parse as parsedate
from airflow.api.common.experimental import trigger_dag

from cwl_airflow.utilities.helpers import get_version, get_dir
from cwl_airflow.utilities.cwl import (
    conf_get,
    slow_cwl_load,
    convert_to_workflow,
    DAG_TEMPLATE
)


class CWLApiBackend():

    # curl -X GET "127.0.0.1:8081/wes/v1/dags" -H "accept: application/json"
    # curl -X GET "127.0.0.1:8081/wes/v1/dags?dag_ids=example_bash_operator" -H "accept: application/json"
    # curl -X GET "127.0.0.1:8081/wes/v1/dags?dag_ids=example_bash_operator,tutorial" -H "accept: application/json"

    # curl -X GET "127.0.0.1:8081/wes/v1/dag_runs?dag_id=example_bash_operator&state=running" -H "accept: application/json"
    # curl -X GET "127.0.0.1:8081/wes/v1/dag_runs?dag_id=example_bash_operator&state=success" -H "accept: application/json"
    # curl -X GET "127.0.0.1:8081/wes/v1/dag_runs?dag_id=example_bash_operator" -H "accept: application/json"
    # curl -X GET "127.0.0.1:8081/wes/v1/dag_runs?state=running" -H "accept: application/json"
    # curl -X GET "127.0.0.1:8081/wes/v1/dag_runs" -H "accept: application/json"

    # curl -X GET "127.0.0.1:8081/wes/v1/dag_runs?run_id=scheduled__2019-07-20T00%3A00%3A00%2B00%3A00" -H "accept: application/json"
    # curl -X GET "127.0.0.1:8081/wes/v1/dag_runs?run_id=scheduled__2019-07-20T00%3A00%3A00%2B00%3A00&dag_id=tutorial" -H "accept: application/json"
    # curl -X GET "127.0.0.1:8081/wes/v1/dag_runs?execution_date=2019-07-20T00%3A00%3A00%2B00%3A00" -H "accept: application/json"

    # curl -X POST "127.0.0.1:8081/wes/v1/dag_runs?dag_id=example_bash_operator&run_id=1234567&conf=%22%7B%7D%22" -H "accept: application/json"
    # curl -X POST "localhost:8081/wes/v1/dags?dag_id=bowtie2-indices" -H "accept: application/json" -H "Content-Type: multipart/form-data" -F "workflow=@bowtie2-indices.cwl"
    # curl -X POST "localhost:8081/wes/v1/dags/bowtie2-indices/dag_runs?run_id=bowtie2_indices_1&conf=%22%7B%7D%22" -H "accept: application/json"
    
    # curl -X GET "127.0.0.1:8081/api/experimental/wes/service-info" -H "accept: application/json"
    # curl -X GET "127.0.0.1:8081/api/experimental/wes/runs" -H "accept: application/json"
    # curl -X POST "127.0.0.1:8081/api/experimental/wes/runs/pracfcizfvmhdefxqdomtxktkbflhgav/cancel" -H "accept: application/json"

    # curl -X GET "127.0.0.1:8081/api/experimental/wes/runs/zlqukumkxxfkumrevclzjcsbyuguhwqy" -H "accept: application/json"
    # curl -X GET "127.0.0.1:8081/api/experimental/wes/runs/pracfcizfvmhdefxqdomtxktkbflhgav/status" -H "accept: application/json"
    # curl -X POST "127.0.0.1:8081/api/experimental/wes/runs" -H "accept: application/json" -H "Content-Type: multipart/form-data" -F "workflow_attachment[]=@custom-bash.cwl"


    def __init__(self):
        get_dir(DAGS_FOLDER)
        self.include_examples = False
        self.dag_template_with_tmp_folder = "#!/usr/bin/env python3\nfrom cwl_airflow import CWLDAG, CWLJobDispatcher, CWLJobGatherer\ndag = CWLDAG(cwl_workflow='{0}', dag_id='{1}', default_args={{'tmp_folder':'{2}'}})\ndag.create()\ndag.add(CWLJobDispatcher(dag=dag), to='top')\ndag.add(CWLJobGatherer(dag=dag), to='bottom')"
        self.wes_state_conversion = {"running": "RUNNING", "success": "COMPLETE", "failed": "EXECUTOR_ERROR"}


    def get_dags(self, dag_ids=[]):
        logging.debug(f"Call get_dags with dag_ids={dag_ids}")
        try:
            dag_ids = dag_ids or self.list_dags()
            logging.debug(f"Processing dags {dag_ids}")
            return {"dags": [{"dag_id": dag_id, "tasks": self.list_tasks(dag_id)} for dag_id in dag_ids]}
        except Exception as err:
            logging.error(f"Failed while running get_dags {err}")
            return {"dags": []}


    def post_dag(self, dag_id=None):
        logging.debug(f"Call post_dag with dag_id={dag_id}")
        try:
            res = self.export_dag(dag_id or ''.join(random.choice(string.ascii_lowercase) for i in range(32)))
            logging.debug(f"Exported DAG {res}")
            return res
        except Exception as err:
            logging.error(f"Failed while running post_dag {err}")
            return connexion.problem(500, "Failed to create dag", str(err))


    def get_dag_runs(self, dag_id=None, run_id=None, execution_date=None, state=None):
        logging.debug(f"Call get_dag_runs with dag_id={dag_id}, run_id={run_id}, execution_date={execution_date}, state={state}")
        try:
            dag_runs = []
            dag_ids = [dag_id] if dag_id else self.list_dags()
            logging.debug(f"Processing dags {dag_ids}")
            for d_id in dag_ids:
                logging.debug(f"Process dag  {d_id}")
                task_ids = self.list_tasks(d_id)
                logging.debug(f"Fetched tasks {task_ids}")
                for dag_run in self.list_dag_runs(d_id, state):
                    logging.debug(f"Process dag run {dag_run['run_id']}, {dag_run['execution_date']}")
                    if run_id and run_id != dag_run["run_id"] or execution_date and execution_date != dag_run["execution_date"]:
                        logging.debug(f"Skip dag_run {dag_run['run_id']}, {dag_run['execution_date']} (run_id or execution_date doesn't match)")
                        continue
                    response_item = {"dag_id": d_id,
                                     "run_id": dag_run["run_id"],
                                     "execution_date": dag_run["execution_date"],
                                     "start_date": dag_run["start_date"],
                                     "state": dag_run["state"],
                                     "tasks": []}
                    logging.debug(f"Get statuses for tasks {task_ids}")
                    for t_id in task_ids:
                        response_item["tasks"].append({"id": t_id, "state": self.task_state(d_id, t_id, dag_run["execution_date"])})
                    dag_runs.append(response_item)
            return {"dag_runs": dag_runs}
        except Exception as err:
            logging.error(f"Failed to call get_dag_runs {err}")
            return {"dag_runs": []}
        

    def post_dag_runs(self, dag_id, run_id=None, conf=None):
        logging.debug(f"Call post_dag_runs with dag_id={dag_id}, run_id={run_id}, conf={conf}")
        try:
            dagrun = self.trigger_dag(dag_id, run_id, conf)
            return {"dag_id": dagrun.dag_id,
                    "run_id": dagrun.run_id,
                    "execution_date": dagrun.execution_date,
                    "start_date": dagrun.start_date,
                    "state": dagrun.state}
        except Exception as err:
            logging.error(f"Failed to call post_dag_runs {err}")
            return connexion.problem(500, "Failed to create dag_run", str(err))


    def post_dag_runs_legacy(self, dag_id):
        data = connexion.request.json
        logging.debug(f"Call post_dag_runs_legacy with dag_id={dag_id}, data={data}")
        return self.post_dag_runs(dag_id, data["run_id"], data["conf"])


    def trigger_dag(self, dag_id, run_id, conf):
        try:
            dag_path = DagModel.get_current(dag_id).fileloc
        except Exception:
            dag_path = path.join(DAGS_FOLDER, dag_id + ".py")

        dag_bag = DagBag(dag_folder=dag_path)
        if not dag_bag.dags:
           logging.info("Failed to import dag due to the following errors")
           logging.info(dag_bag.import_errors)
           logging.info("Sleep for 3 seconds and give it a second try")
           sleep(3)
           dag_bag = DagBag(dag_folder=dag_path)

        triggers = trigger_dag._trigger_dag(
            dag_id=dag_id,
            dag_run=DagRun(),
            dag_bag=dag_bag,
            run_id=run_id,
            conf=conf,
            execution_date=None,
            replace_microseconds=False
        )
        return triggers[0] if triggers else None


    def list_dags(self):
        return DagBag(include_examples=self.include_examples).dags.keys()


    def list_tasks(self, dag_id):
        return [t.task_id for t in DagBag(include_examples=self.include_examples).dags[dag_id].tasks]


    def task_state(self, dag_id, task_id, execution_date):
        task_state = TaskInstance(DagBag(include_examples=self.include_examples).dags[dag_id].get_task(task_id=task_id), parsedate(execution_date)).current_state()
        task_state = task_state or "none"
        return task_state


    def list_dag_runs(self, dag_id, state):
        dag_runs = []
        for dag_run in DagRun.find(dag_id=dag_id, state=state):
            dag_runs.append({
                "run_id": dag_run.run_id,
                "state": dag_run.state,
                "execution_date": dag_run.execution_date.isoformat(),
                "start_date": ((dag_run.start_date or '') and dag_run.start_date.isoformat())
            })
        return dag_runs


    def save_attachment(self, attachment, location, exist_ok=False):
        if path.isfile(location) and not exist_ok:
            raise FileExistsError("[Errno 17] File exists: '" + location + "'")
        data = connexion.request.files[attachment]
        data.save(location)
    

    def export_dag(self, dag_id):
        cwl_path = path.join(DAGS_FOLDER, dag_id + ".cwl")
        dag_path = path.join(DAGS_FOLDER, dag_id + ".py")
        self.save_attachment("workflow", cwl_path)
        convert_to_workflow(
            command_line_tool=slow_cwl_load(
                workflow=cwl_path,
                only_tool=True
            ),
            location=cwl_path
        )
        with open(dag_path, 'x') as output_stream:
            output_stream.write(DAG_TEMPLATE.format(cwl_path, dag_id))
        return {"dag_id": dag_id, "cwl_path": cwl_path, "dag_path": dag_path}

###########################################################################
# WES                                                                     #
###########################################################################
 
    def wes_collect_attachments(self, run_id):
        tempdir = tempfile.mkdtemp(
            dir=get_dir(
                path.abspath(
                    conf_get("cwl", "tmp_folder", os.path.join(AIRFLOW_HOME, "cwl_tmp_folder"))
                )
            ),
            prefix="run_id_"+run_id+"_"
        )
        logging.debug(f"Save all attached files to {tempdir}")
        for k, ls in iterlists(connexion.request.files):
            logging.debug(f"Process attachment parameter {k}")
            if k == "workflow_attachment":
                for v in ls:
                    try:
                        logging.debug(f"Process attached file {v}")
                        sp = v.filename.split("/")
                        fn = []
                        for p in sp:
                            if p not in ("", ".", ".."):
                                fn.append(secure_filename(p))
                        dest = path.join(tempdir, *fn)
                        if not path.isdir(path.dirname(dest)):
                            get_dir(path.dirname(dest))
                        logging.debug(f"Save {v.filename} to {dest}")
                        v.save(dest)
                    except Exception as err:
                        raise ValueError(f"Failed to process attached file {v}, {err}")
        body = {}       
        for k, ls in iterlists(connexion.request.form):
            logging.debug(f"Process form parameter {k}")
            for v in ls:
                try:
                    if not v:
                        continue
                    if k == "workflow_params":
                        job_file = path.join(tempdir, "job.json")
                        with open(job_file, "w") as f:
                            json.dump(json.loads(v), f, indent=4)
                        logging.debug(f"Save job file to {job_file}")
                        loader = Loader(load.jobloaderctx.copy())
                        job_order_object, _ = loader.resolve_ref(job_file, checklinks=False)
                        body[k] = job_order_object
                    else:
                        body[k] = v
                except Exception as err:
                    raise ValueError(f"Failed to process form parameter {k}, {v}, {err}")

        if "workflow_params" not in body or "workflow_url" not in body:
            raise ValueError("Missing 'workflow_params' or 'workflow_url' in submission")
        
        body["workflow_url"] = path.join(tempdir, secure_filename(body["workflow_url"]))

        return tempdir, body


    def wes_get_service_info(self):
        logging.debug(f"Call wes_get_service_info")
        response = {
            "workflow_type_versions": {
                "CWL": {"workflow_type_version": ["v1.0"]}
            },
            "supported_wes_versions": ["1.0.0"],
            "supported_filesystem_protocols": ["file"],
            "workflow_engine_versions": {
                "cwl-airflow": get_version()
            }
        }
        return response


    def wes_list_runs(self, page_size=None, page_token=None):
        logging.debug(f"Call wes_list_runs with page_size={page_size}, page_token={page_token}")
        logging.debug(f"page_size and page_token are currently ignored by cwl-airflow api server")
        dag_run_info = self.get_dag_runs()
        return [{"run_id": item["run_id"], "state": self.wes_state_conversion[item["state"]]} for item in dag_run_info["dag_runs"] ]


    def wes_run_workflow(self):
        logging.debug(f"Call wes_run_workflow")
        run_id = ''.join(random.choice(string.ascii_lowercase) for i in range(32))
        try:
            tempdir, body = self.wes_collect_attachments(run_id)
            with open(path.join(DAGS_FOLDER, run_id + ".py"), 'x') as o_stream:
                o_stream.write(self.dag_template_with_tmp_folder.format(body["workflow_url"], run_id, tempdir))
            self.post_dag_runs(dag_id=run_id, run_id=run_id, conf=json.dumps({"job": body["workflow_params"]}))
            return {"run_id": run_id}
        except Exception as err:
            logging.debug(f"Failed to run workflow {err}")
            return connexion.problem(500, "Failed to run workflow", str(err))
        

    def wes_get_run_log(self, run_id):
        logging.debug(f"Call wes_get_run_log with {run_id}")
        try:
            dag_run_info = self.get_dag_runs(dag_id=run_id, run_id=run_id)["dag_runs"][0]
            dag_run = DagRun.find(dag_id=run_id, state=None)[0]
            workflow_params = dag_run.conf["job"]
            del workflow_params["id"]
            workflow_outputs = {}
            try:
                results_location = dag_run.get_task_instance(task_id="CWLJobGatherer").xcom_pull()
                with open(results_location, "r") as input_stream:
                    workflow_outputs = json.load(input_stream)
            except Exception as err:
                logging.debug(f"Failed to read workflow results from file. \n {err}")
            return {
                "run_id": run_id,
                "request": {"workflow_params": workflow_params},
                "state": self.wes_state_conversion[dag_run_info["state"]],
                "run_log": {
                    "name": run_id,
                    "cmd": [""],
                    "start_time": dag_run_info["start_date"],
                    "end_time": "",
                    "stdout": "",
                    "stderr": "",
                    "exit_code": ""
                },
                "task_logs": [{"name": task["id"]} for task in dag_run_info["tasks"]],
                "outputs": workflow_outputs
            }
        except Exception as err:
            logging.debug(f"Failed to fetch infromation for {run_id}")
            return {}


    def wes_get_run_status(self, run_id):
        logging.debug(f"Call wes_get_run_status with run_id={run_id}")
        try:
            dag_run_info = self.get_dag_runs(dag_id=run_id, run_id=run_id)["dag_runs"][0]
            return {"run_id": dag_run_info["run_id"], "state": self.wes_state_conversion[dag_run_info["state"]]}
        except Exception as err:
            logging.debug(f"Failed to fetch infromation for {run_id}")
            return {}


    def wes_cancel_run(self, run_id):
        logging.debug(f"Call wes_cancel_run with run_id={run_id}")
        try:
            dag_run = DagRun.find(dag_id=run_id, state=None)[0]
            self.stop_tasks(dag_run)
            self.remove_tmp_data(dag_run)
            return {"run_id": run_id}
        except Exception as err:
            logging.debug(f"Failed to cancel dag run {run_id}, {err}")
            return connexion.problem(500, f"Failed to cancel dag run {run_id}", str(err))


    def stop_tasks(self, dr):
        logging.debug(f"Stop tasks for {dr.dag_id} - {dr.run_id}")
        for ti in dr.get_task_instances():
            logging.debug(f"process {ti.dag_id} - {ti.task_id} - {ti.execution_date} - {ti.pid}")
            if ti.state == State.RUNNING:
                try:
                    process = psutil.Process(ti.pid) if ti.pid else None
                except Exception:
                    logging.debug(f" - cannot find process by PID {ti.pid}")
                    process = None
                ti.set_state(State.FAILED)
                logging.debug(" - set state to FAILED")
                if process:
                    logging.debug(f" - wait for process {ti.pid} to exit")
                    try:
                        cleanup_timeout = int(conf_get("core", "KILLED_TASK_CLEANUP_TIME", 60)) * 2
                        process.wait(timeout=cleanup_timeout)  # raises psutil.TimeoutExpired if timeout. Makes task fail -> DagRun fails
                    except psutil.TimeoutExpired as e:
                        logging.debug(f" - Done waiting for process {ti.pid} to die")


    def remove_tmp_data(self, dr):
        logging.debug(f"Remove tmp data for {dr.dag_id} - {dr.run_id}")
        tmp_folder = None
        try:
            results_location = dr.get_task_instance(task_id="CWLJobDispatcher").xcom_pull()
            with open(results_location, "r") as input_stream:
                dispatcher_outputs = json.load(input_stream)
                tmp_folder = dispatcher_outputs.get("tmp_folder")
        except Exception as err:
            logging.debug(f"Failed to read dispathcer results from file. \n {err}")
        try:
            shutil.rmtree(tmp_folder)
            logging.debug(f"Successfully removed {tmp_folder}")
        except Exception as ex:
            logging.error(f"Failed to delete temporary output directory {tmp_folder}\n {ex}")