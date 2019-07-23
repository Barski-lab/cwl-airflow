import os
import subprocess
import logging


logger = logging.getLogger(__name__)


class CWLAirflowBackend():

    # curl -X GET "127.0.0.1:8080/wes/v1/dags" -H "accept: application/json"
    # curl -X GET "127.0.0.1:8080/wes/v1/dags?dag_ids=example_bash_operator" -H "accept: application/json"
    # curl -X GET "127.0.0.1:8080/wes/v1/dags?dag_ids=example_bash_operator,tutorial" -H "accept: application/json"

    # curl -X GET "127.0.0.1:8080/wes/v1/dag_runs?dag_id=example_bash_operator&state=running" -H "accept: application/json"
    # curl -X GET "127.0.0.1:8080/wes/v1/dag_runs?dag_id=example_bash_operator&state=success" -H "accept: application/json"
    # curl -X GET "127.0.0.1:8080/wes/v1/dag_runs?dag_id=example_bash_operator" -H "accept: application/json"
    # curl -X GET "127.0.0.1:8080/wes/v1/dag_runs?state=running" -H "accept: application/json"
    # curl -X GET "127.0.0.1:8080/wes/v1/dag_runs" -H "accept: application/json"

    # curl -X GET "127.0.0.1:8080/wes/v1/dag_runs?run_id=scheduled__2019-07-20T00%3A00%3A00%2B00%3A00" -H "accept: application/json"
    # curl -X GET "127.0.0.1:8080/wes/v1/dag_runs?run_id=scheduled__2019-07-20T00%3A00%3A00%2B00%3A00&dag_id=tutorial" -H "accept: application/json"
    # curl -X GET "127.0.0.1:8080/wes/v1/dag_runs?execution_date=2019-07-20T00%3A00%3A00%2B00%3A00" -H "accept: application/json"

    env = None


    def __init__(self):
        extend_env = {"AIRFLOW__CORE__LOGGING_LEVEL": "ERROR"}
        self.env = os.environ.copy()
        self.env.update(extend_env)


    def get_dags(self, dag_ids=[]):
        logger.debug(f"""Call get_dags with dag_ids={dag_ids}""")
        response = {"dags": []}
        try:
            dag_ids = dag_ids if dag_ids else self.list_dags()
            logger.debug(f"""Processing dags {dag_ids}""")
            response = {"dags": [{"dag_id": dag_id, "tasks": self.list_tasks(dag_id)} for dag_id in dag_ids]}
        except Exception as err:
            logger.error("Failed while running get_dags", err)
        return response


    def get_dag_runs(self, dag_id=None, run_id=None, execution_date=None, state=None):
        logger.debug(f"""Call get_dag_runs with dag_id={dag_id}, run_id={run_id}, execution_date={execution_date}, state={state}""")
        response = {"dag_runs": []}
        try:
            dag_runs = []
            dag_ids = [dag_id] if dag_id else self.list_dags()
            logger.debug(f"""Processing dags {dag_ids}""")
            for d_id in dag_ids:
                logger.debug(f"""Process dag  {d_id}""")
                task_ids = self.list_tasks(d_id)
                for dag_run in self.list_dag_runs(d_id, state):
                    if run_id and run_id != dag_run["run_id"] or execution_date and execution_date != dag_run["execution_date"]:
                        logger.debug(f"""Skip dag_run {dag_run["run_id"]} (run_id or execution_date doesn't match)""")
                        continue
                    logger.debug(f"""Process dag run {dag_run["run_id"]}""")
                    response_item = {"dag_id": d_id,
                                     "run_id": dag_run["run_id"],
                                     "execution_date": dag_run["execution_date"],
                                     "state": dag_run["state"],
                                     "tasks": []}    
                    for t_id in task_ids:
                        response_item["tasks"].append({"id": t_id, "state": self.task_state(d_id, t_id, dag_run["execution_date"])})
                    dag_runs.append(response_item)
            response["dag_runs"] = dag_runs
        except Exception as err:
            logger.error(f"""Failed to call get_dag_runs {err}""" )
        return response
    

    def list_dags(self):
        logger.debug(f"""List all dags""")
        list_dags = subprocess.run(["airflow", "list_dags"], capture_output=True, text=True, env=self.env)
        list_dags.check_returncode()
        dags_raw = list_dags.stdout.split("\n")
        return [i.strip() for i in dags_raw[dags_raw.index("DAGS")+2:] if i.strip()]


    def list_tasks(self, dag_id):
        logger.debug(f"""List tasks of {dag_id}""")
        list_tasks = subprocess.run(["airflow", "list_tasks", dag_id], capture_output=True, text=True, env=self.env)
        list_tasks.check_returncode()
        tasks_raw = list_tasks.stdout.split("\n")
        return [i.strip() for i in tasks_raw if i.strip()]


    def task_state(self, dag_id, task_id, execution_date):
        logger.debug(f"""Get {task_id} state of {dag_id} with execution date {execution_date}""")
        task_state = subprocess.run(["airflow", "task_state", dag_id, task_id, execution_date], capture_output=True, text=True, env=self.env)
        task_state.check_returncode()
        return task_state.stdout.strip()


    def list_dag_runs(self, dag_id, state):
        logger.debug(f"""List dag runs of {dag_id} with state {state}""")
        list_dag_runs_cmd = ["airflow", "list_dag_runs", dag_id]
        if state:
            list_dag_runs_cmd.extend(["--state", state])
        list_dag_runs = subprocess.run(list_dag_runs_cmd, capture_output=True, text=True, env=self.env)
        list_dag_runs.check_returncode()
        dag_runs_raw = list_dag_runs.stdout.split("\n")
        return [
                    {
                        "run_id": i.split("|")[1].strip(),
                        "state": i.split("|")[2].strip(),
                        "execution_date": i.split("|")[3].strip()
                    }
                    for i in dag_runs_raw[dag_runs_raw.index("DAG RUNS")+3:] if i.strip()
               ]
