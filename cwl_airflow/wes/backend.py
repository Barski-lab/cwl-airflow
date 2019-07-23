import os
import subprocess
import logging


logger = logging.getLogger(__name__)


class CWLAirflowBackend():

    env = None

    def __init__(self):
        extend_env = {"AIRFLOW__CORE__LOGGING_LEVEL": "ERROR"}
        self.env = os.environ.copy()
        self.env.update(extend_env)

    def list_dags(self):
        # curl -X GET "127.0.0.1:8080/wes/v1/dags" -H "accept: application/json"
        response = {"dags": []}
        try:
            list_dags = subprocess.run(["airflow", "list_dags"], capture_output=True, text=True, env=self.env)
            list_dags.check_returncode()
            dags_raw = list_dags.stdout.split("\n")
            response["dags"] = [i.strip() for i in dags_raw[dags_raw.index("DAGS")+2:] if i.strip()]
        except subprocess.CalledProcessError as err:
            logger.error("Failed to call list_dags", err)
        return response

    def list_dag_runs(self, dag_id=None, state=None):
        # curl -X GET "127.0.0.1:8080/wes/v1/dag_runs?dag_id=example_bash_operator&state=running" -H "accept: application/json"
        # curl -X GET "127.0.0.1:8080/wes/v1/dag_runs?dag_id=example_bash_operator" -H "accept: application/json"
        # curl -X GET "127.0.0.1:8080/wes/v1/dag_runs?state=running" -H "accept: application/json"
        # curl -X GET "127.0.0.1:8080/wes/v1/dag_runs" -H "accept: application/json"
        response = {"dag_runs": []}
        try:
            dags = [dag_id] if dag_id else self.list_dags()["dags"]
            for dag in dags:
                list_dag_runs_cmd = ["airflow", "list_dag_runs", dag]
                if state:
                    list_dag_runs_cmd.extend(["--state", state])
                list_dag_runs = subprocess.run(list_dag_runs_cmd, capture_output=True, text=True, env=self.env)
                list_dag_runs.check_returncode()
                dag_runs_raw = list_dag_runs.stdout.split("\n")
                response["dag_runs"].extend([
                                                {
                                                    "dag_id": dag,
                                                    "run_id": i.split("|")[1].strip(),
                                                    "state": i.split("|")[2].strip(),
                                                    "execution_date": i.split("|")[3].strip()
                                                }
                                                for i in dag_runs_raw[dag_runs_raw.index("DAG RUNS")+3:] if i.strip()
                                            ])
        except subprocess.CalledProcessError as err:
            logger.error("Failed to call list_dag_runs", err)
        return response
    
    def list_tasks(self, dag_id=None):
        # curl -X GET "127.0.0.1:8080/wes/v1/tasks" -H "accept: application/json"
        # curl -X GET "127.0.0.1:8080/wes/v1/tasks?dag_id=example_bash_operator" -H "accept: application/json"
        response = {"tasks": []}
        try:
            dags = [dag_id] if dag_id else self.list_dags()["dags"]
            for dag in dags:
                list_tasks_cmd = ["airflow", "list_tasks", dag]
                list_tasks = subprocess.run(list_tasks_cmd, capture_output=True, text=True, env=self.env)
                list_tasks.check_returncode()
                tasks_raw = list_tasks.stdout.split("\n")
                response["tasks"].append({
                                            "dag_id": dag,
                                            "tasks": [i.strip() for i in tasks_raw if i.strip()]
                                         })
        except subprocess.CalledProcessError as err:
            logger.error("Failed to call list_tasks", err)
        return response
