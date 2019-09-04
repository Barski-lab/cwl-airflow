import subprocess
import logging
import connexion
import random
import string

from os import path, environ, makedirs
from airflow.models import DagBag, TaskInstance, DagRun
from airflow.utils.timezone import parse as parsedate
from airflow.api.common.experimental import trigger_dag
from airflow.settings import DAGS_FOLDER


logger = logging.getLogger(__name__)


class CWLAirflowBackend():

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

    env = None
    include_examples = False
    dag_template = "#!/usr/bin/env python3\nfrom cwl_airflow import CWLDAG, CWLJobDispatcher, CWLJobGatherer\ndag = CWLDAG(cwl_workflow='{0}', dag_id='{1}')\ndag.create()\ndag.add(CWLJobDispatcher(dag=dag), to='top')\ndag.add(CWLJobGatherer(dag=dag), to='bottom')"


    def __init__(self):
        makedirs(DAGS_FOLDER, mode=0o0775, exist_ok=True)
        extend_env = {"AIRFLOW__CORE__LOGGING_LEVEL": "ERROR"}
        self.env = environ.copy()
        self.env.update(extend_env)


    def get_dags(self, dag_ids=[]):
        logger.debug(f"""Call get_dags with dag_ids={dag_ids}""")
        try:
            dag_ids = dag_ids or self.list_dags()
            logger.debug(f"""Processing dags {dag_ids}""")
            return {"dags": [{"dag_id": dag_id, "tasks": self.list_tasks(dag_id)} for dag_id in dag_ids]}
        except Exception as err:
            logger.error(f"""Failed while running get_dags {err}""")
            return {"dags": []}


    def post_dag(self, dag_id=None):
        logger.debug(f"""Call post_dag with dag_id={dag_id}""")
        try:
            res = self.export_dag(dag_id or ''.join(random.choice(string.ascii_lowercase) for i in range(32)))
            logger.debug(f"""Exported DAG {res}""")
            return res
        except Exception as err:
            logger.error(f"""Failed while running post_dag {err}""")
            return connexion.problem(500, "Failed to create dag", str(err))


    def get_dag_runs(self, dag_id=None, run_id=None, execution_date=None, state=None):
        logger.debug(f"""Call get_dag_runs with dag_id={dag_id}, run_id={run_id}, execution_date={execution_date}, state={state}""")
        try:
            dag_runs = []
            dag_ids = [dag_id] if dag_id else self.list_dags()
            logger.debug(f"""Processing dags {dag_ids}""")
            for d_id in dag_ids:
                logger.debug(f"""Process dag  {d_id}""")
                task_ids = self.list_tasks(d_id)
                logger.debug(f"""Fetched tasks {task_ids}""")
                for dag_run in self.list_dag_runs(d_id, state):
                    logger.debug(f"""Process dag run {dag_run["run_id"]}, {dag_run["execution_date"]}""")
                    if run_id and run_id != dag_run["run_id"] or execution_date and execution_date != dag_run["execution_date"]:
                        logger.debug(f"""Skip dag_run {dag_run["run_id"]}, {dag_run["execution_date"]} (run_id or execution_date doesn't match)""")
                        continue
                    response_item = {"dag_id": d_id,
                                     "run_id": dag_run["run_id"],
                                     "execution_date": dag_run["execution_date"],
                                     "start_date": dag_run["start_date"],
                                     "state": dag_run["state"],
                                     "tasks": []}
                    logger.debug(f"""Get statuses for tasks {task_ids}""")
                    for t_id in task_ids:
                        response_item["tasks"].append({"id": t_id, "state": self.task_state(d_id, t_id, dag_run["execution_date"])})
                    dag_runs.append(response_item)
            return {"dag_runs": dag_runs}
        except Exception as err:
            logger.error(f"""Failed to call get_dag_runs {err}""")
            return {"dag_runs": []}
        

    def post_dag_runs(self, dag_id, run_id=None, conf=None):
        logger.debug(f"""Call post_dag_runs with dag_id={dag_id}, run_id={run_id}, conf={conf}""")
        try:
            dagrun = self.trigger_dag(dag_id, run_id, conf)
            return {"dag_id": dagrun.dag_id,
                    "run_id": dagrun.run_id,
                    "execution_date": dagrun.execution_date,
                    "start_date": dagrun.start_date,
                    "state": dagrun.state}
        except Exception as err:
            logger.error(f"""Failed to call post_dag_runs {err}""")
            return connexion.problem(500, "Failed to create dag_run", str(err))


    def post_dag_runs_legacy(self, dag_id):
        data = connexion.request.json
        logger.debug(f"""Call post_dag_runs_legacy with dag_id={dag_id}, data={data}""")
        return self.post_dag_runs(dag_id, data["run_id"], data["conf"])


    def trigger_dag(self, dag_id, run_id, conf):
        try:
            dag_path = DagModel.get_current(dag_id).fileloc
        except Exception:
            dag_path = path.join(DAGS_FOLDER, dag_id + ".py")
        triggers = trigger_dag._trigger_dag(
            dag_id=dag_id,
            dag_run=DagRun(),
            dag_bag=DagBag(dag_folder=dag_path),
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
                'run_id': dag_run.run_id,
                'state': dag_run.state,
                'execution_date': dag_run.execution_date.isoformat(),
                'start_date': ((dag_run.start_date or '') and dag_run.start_date.isoformat())
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
        with open(dag_path, 'x') as o_stream:
            o_stream.write(self.dag_template.format(cwl_path, dag_id))
        return {"dag_id": dag_id, "cwl_path": cwl_path, "dag_path": dag_path}