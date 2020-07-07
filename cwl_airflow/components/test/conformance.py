import os
import sys
import uuid
import json
import queue
import logging
import requests
import itertools
import threading
import socketserver

from time import sleep
from shutil import rmtree
from collections import OrderedDict
from airflow.settings import DAGS_FOLDER
from cwltest.utils import compare, CompareFail
from http.server import SimpleHTTPRequestHandler

from cwl_airflow.utilities.helpers import (
    load_yaml,
    get_dir,
    get_absolute_path,
    get_rootname
)
from cwl_airflow.utilities.cwl import (
    load_job,
    DAG_TEMPLATE
)


def get_listener_thread(
    results_queue,
    port,
    daemon
):
    httpd = socketserver.TCPServer(("", port), CustomHandler)
    httpd.results_queue = results_queue                            # to have access to results_queue from CustomHandler through self.server.results_queue
    return threading.Thread(
        target=httpd.serve_forever,
        daemon=daemon
    )


def get_spinner_thread():
    return threading.Thread(target=spin, daemon=True)


def get_checker_thread(
    suite_data,
    results_queue,
    daemon
):
    return threading.Thread(target=check_result,
                            daemon=daemon,
                            kwargs={
                                "suite_data": suite_data,
                                "results_queue": results_queue
                            })


class CustomHandler(SimpleHTTPRequestHandler):

    def do_POST(self):
        self.send_response(200)
        self.end_headers()
        if "status" in self.path:
            return None
        payload = json.loads(
            self.rfile.read(
                int(self.headers["Content-Length"])
            ).decode("UTF-8")
        )["payload"]
        if payload.get("results", None) or payload.get("state", None) == "failed":
            self.server.results_queue.put({
                "run_id":  payload["run_id"],
                "dag_id":  payload["dag_id"],
                "results": payload.get("results", None)
            })


def spin():
    spinner = itertools.cycle(['-', '/', '|', '\\'])
    while True:
        sys.stdout.write(next(spinner))
        sleep(0.1)
        sys.stdout.flush()
        sys.stdout.write('\b')


def check_result(suite_data, results_queue):
    processed = 0
    while processed < len(suite_data):
        try:
            item = results_queue.get()
        except queue.Empty:
            continue
        processed = processed + 1
        run_id = item["run_id"]
        logging.info(f"Check results for {run_id}")
        try:
            compare(suite_data[run_id]["output"], item["results"])
        except CompareFail as ex:
            suite_data[run_id]["error"] = str(ex)
        finally:
            rmtree(suite_data[run_id]["job"]["outputs_folder"])


def load_test_suite(args):
    """
    Loads tests from the provided --suite file.
    Selects tests based on the indices from --range.
    
    Updates tools locations to be absolute, loads
    jobs and updates all inputs files locations to
    be absolute too. Adds "outputs_folder" to the job

    Adds run_id's as keys for easy access and proper
    test identification when receiving results.
    """

    suite_data = load_yaml(args.suite)
    suite_dir = os.path.dirname(args.suite)
    suite_data_filtered = OrderedDict()                                       # use OrderedDict just to keep it similar to suite_data
    for i in args.range:
        test_data = suite_data[i]
        run_id = str(uuid.uuid4())
        tool_location = get_absolute_path(test_data["tool"], suite_dir)
        job_data = load_job(
            workflow=tool_location,
            job=get_absolute_path(test_data["job"], suite_dir)
        )
        job_data["outputs_folder"] = get_dir(os.path.join(args.tmp, run_id))

        test_data.update({
            "job":  job_data,                                                 # already parsed, includes "outputs_folder"
            "tool": tool_location,
            "dag_id": get_rootname(test_data["tool"])
        })

        suite_data_filtered[run_id] = test_data                               # use "run_id" as a key for fast access when checking results
    return suite_data_filtered


def create_dags(suite_data, dags_folder=None):
    """
    Iterates over suite_data and exports DAG files into dags_folder.
    If file with the same name has already been exported, skip it.
    If dags_folder is not set, use DAGS_FOLDER from airflow.settings

    TODO: maybe I will need to copy packed cwl file into the dags_folder too.
    """

    dags_folder = get_dir(DAGS_FOLDER if dags_folder is None else dags_folder)

    for test_data in suite_data.values():
        dag_location = os.path.join(
            dags_folder,
            test_data["dag_id"] + ".py"
        )
        if not os.path.isfile(dag_location):
            with open(dag_location, "w") as output_stream:
                output_stream.write(
                    DAG_TEMPLATE.format(
                        test_data["tool"],
                        test_data["dag_id"]
                    )
                )


def trigger_dags(suite_data, args):
    for run_id, test_data in suite_data.items():
        logging.info(f"Trigger DAG {test_data['dag_id']} as {run_id}")
        r = requests.post(
            url=args.endpoint,
            params={
                "run_id": run_id,
                "dag_id": test_data["dag_id"],
                "conf": json.dumps(
                    {
                        "job": test_data["job"]
                    }
                )
            }
        )


def print_report(suite_data):
    exit_code = 0
    for run_id, test_data in suite_data.items():
        if "error" in test_data:
            exit_code = 1
            logging.error(f"Test {test_data['dag_id']} run as {run_id} failed")
            logging.debug(test_data)
        else:
            logging.info(f"Test {test_data['dag_id']} run as {run_id} finished successfully")
    return exit_code


def run_test_conformance(args):
    """
    Runs conformance tests
    """

    # Load test suite data, setup a queue to keep results
    suite_data = load_test_suite(args)
    results_queue = queue.Queue(maxsize=len(suite_data))

    # Create new dags
    create_dags(suite_data)                       # TODO: should call API instead of manually creating new DAGs

    # Start thread to listen for status updates
    listener = get_listener_thread(
        results_queue=results_queue,
        port=args.port,
        daemon=True
    )
    listener.start()

    # Start checker thread to evaluate received results
    checker = get_checker_thread(
        suite_data=suite_data,
        results_queue=results_queue,
        daemon=False
    )
    checker.start()

    # Trigger all dags
    trigger_dags(suite_data, args)

    # Display spinner if  --spin
    if args.spin:
        spinner = get_spinner_thread()
        spinner.start()

    # Wait until all triggered dags return results
    checker.join()

    exit_code = print_report(suite_data)

    sys.exit(exit_code)