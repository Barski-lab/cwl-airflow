import subprocess
import logging


logger = logging.getLogger(__name__)


class CWLAirflowBackend():

    def list_dags(self):
        """curl -X GET "127.0.0.1:8080/wes/v1/dags" -H "accept: application/json""""
        response = {"dags": []}
        try:
            list_dags = subprocess.run(["airflow", "list_dags"], capture_output=True, text=True)
            list_dags.check_returncode()
            dags_raw = list_dags.stdout.split("\n")
            response["dags"] = [i for i in dags_raw[dags_raw.index("DAGS")+2:] if i.strip()]
        except subprocess.CalledProcessError as err:
            logger.error("Failed to call list_dags", err)
        return response

    def list_dag_runs(self, dag_id=None, state=None):
        """curl -X GET "127.0.0.1:8080/wes/v1/dag_runs?dag_id=example_bash_operator&state=running" -H "accept: application/json""""
        response = {"dag_runs": []}
        try:
            dags = [dag_id] if dag_id else self.list_dags()["dags"]
            for dag in dags:
                list_dag_runs_cmd = ["airflow", "list_dag_runs", dag]
                if state:
                    list_dag_runs_cmd.extend(["--state", state])
                list_dag_runs = subprocess.run(list_dag_runs_cmd, capture_output=True, text=True)
                list_dag_runs.check_returncode()
                dag_runs_raw = list_dag_runs.stdout.split("\n")
                dag_runs = [ [i.split("|")[1].strip(), i.split("|")[2].strip(), i.split("|")[3].strip()] for i in dag_runs_raw[dag_runs_raw.index("DAG RUNS")+3:] if i.strip() ]
                for dag_run in dag_runs:
                    response["dag_runs"].append({
                        "dag_id": dag,
                        "run_id": dag_run[0],
                        "state": dag_run[1],
                        "execution_date": dag_run[2]
                    })
        except subprocess.CalledProcessError as err:
            logger.error("Failed to call list_dag_runs", err)
        return response