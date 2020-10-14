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
from urllib.parse import urljoin
from collections import OrderedDict
from cwltest.utils import compare, CompareFail
from http.server import SimpleHTTPRequestHandler

from cwl_airflow.utilities.helpers import (
    load_yaml,
    get_dir,
    get_absolute_path,
    get_rootname,
    get_api_failure_reason,
    get_compressed
)
from cwl_airflow.utilities.cwl import (
    load_job,
    embed_all_runs,
    fast_cwl_load
)


def get_listener_thread(                                       # safe to kill when run as daemon
    results_queue,
    port,
    daemon
):
    httpd = socketserver.TCPServer(("127.0.0.1", port), CustomHandler)
    httpd.results_queue = results_queue                        # to have access to results_queue from CustomHandler through self.server.results_queue
    return threading.Thread(
        target=httpd.serve_forever,
        daemon=daemon
    )


def get_spinner_thread(daemon):                                # safe to kill when run as daemon
    return threading.Thread(target=spin, daemon=daemon)


def get_checker_thread(                                        # is not thread safe when writing to "suite_data"
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

    def log_message(self, format, *args):  # to suppress logging on each POST 200 response sent
        pass

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
        if "results" in payload or payload.get("state", None) == "failed":     # "results" can be {}, so we should check only if key is present, but not value
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


def get_unfinished_runs(suite_data):
    """
    Selects only those items from "suite_data" that
    are not finished yet, so we can wait for their
    results
    """

    suite_data_unfinished = OrderedDict()
    for run_id, test_data in suite_data.items():
        if not test_data["finished"]:
            suite_data_unfinished[run_id] = test_data
    return suite_data_unfinished


def check_result(suite_data, results_queue):
    previous_unfinished_count = None
    while True:
        suite_data_unfinished = get_unfinished_runs(suite_data)
        if len(suite_data_unfinished) == 0:
            break
        try:
            item = results_queue.get(False)
        except queue.Empty:
            unfinished_count = len(suite_data_unfinished)
            if previous_unfinished_count != unfinished_count:
                logging.info(f"Waiting for {unfinished_count} unfinished runs:")
                for run_id, test_data in suite_data_unfinished.items():
                    logging.info(f"   test case - {test_data['index']}, dag_id - {test_data['dag_id']}, run_id - {run_id}")   
                previous_unfinished_count = unfinished_count
            sleep(10)                                       # sleep for 10 second before trying to fetch new results from the empty queue
            continue
        run_id = item["run_id"]
        test_data = suite_data_unfinished[run_id]  # if this fails, look for a bug
        logging.info(f"Check results from the test case {test_data['index']} that runs DAG {test_data['dag_id']} as {run_id}")
        try:
            compare(test_data["output"], item["results"])
        except (CompareFail, KeyError) as ex:               # catch KeyError in case output field is missing for tool that should fail
            if not test_data.get("should_fail", None):      # do not report error if tool should fail
                test_data["error"] = str(ex)
        finally:
            test_data["finished"] = True
            rmtree(test_data["job"]["outputs_folder"])


def load_test_suite(args):
    """
    Loads tests from the provided --suite file.
    Selects tests based on the indices from --range.
    
    Updates tools locations to be absolute, loads
    jobs and updates all inputs files locations to
    be absolute too. Adds "outputs_folder" to the job,
    as well as the "index" to indicate which test case
    was used.

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
        logging.info(f"Read test case {i+1} to run {tool_location}")

        job_location = None
        job_data = {}

        if "job" in test_data:
            job_location = get_absolute_path(test_data["job"], suite_dir)
            job_data = load_job(
                workflow=tool_location,
                job=job_location
            )

        job_data["outputs_folder"] = get_dir(os.path.join(args.tmp, run_id))

        test_data.update({
            "job":  job_data,                                                 # already parsed, includes "outputs_folder"
            "tool": tool_location,
            "dag_id": get_rootname(test_data["tool"]),
            "index": i+1,                                                     # to know test case number, 1-based to correspond to --range
            "finished": False                                                 # to indicate whether the test was finished or not
        })
        logging.info(f"Successfully loaded test case {i+1} to run {tool_location} with {job_location} as {run_id}")
        suite_data_filtered[run_id] = test_data                               # use "run_id" as a key for fast access when checking results
    return suite_data_filtered


def create_dags(suite_data, args, dags_folder=None):
    """
    Iterates over "suite_data" and creates new DAGs. Tries to include
    all tools into the worfklow before sending it to the API server.
    If loaded tool is not Workflow, send it unchanged. It's safe to
    not process errors when we failed to add new DAG. Airflow Scheduler
    will parse all dags at the end of the next "dag_dir_list_interval"
    from airflow.cfg. If args.embed was True, send base64 encoded zlib
    compressed content of the workflow file instead of attaching it.
    """

    # TODO: Do we need to force scheduler to reload DAGs after all DAG added?

    for test_data in suite_data.values():
        workflow_path = os.path.join(
            args.tmp,
            os.path.basename(test_data["tool"])
        )
        embed_all_runs(                                                                               # will save results to "workflow_path"
            workflow_tool=fast_cwl_load(test_data["tool"]),
            location=workflow_path
        )
        with open(workflow_path, "rb") as input_stream:
            logging.info(f"Add DAG {test_data['dag_id']} from test case {test_data['index']}")

            if args.embed:                                                                            # send base64 encoded zlib compressed workflow content that will be embedded into DAG python file
                logging.info(f"Sending base64 encoded zlib compressed content from {workflow_path}")
                r = requests.post(
                    url=urljoin(args.api, "/api/experimental/dags"),
                    params={
                        "dag_id": test_data["dag_id"]
                    },
                    json={"workflow_content": get_compressed(input_stream)}
                )
            else:                                                                                     # attach workflow as a file
                logging.info(f"Attaching workflow file {workflow_path}")
                r = requests.post(
                    url=urljoin(args.api, "/api/experimental/dags"),
                    params={
                        "dag_id": test_data["dag_id"]
                    },
                    files={"workflow": input_stream}
                )

            # Check if we failed to add new DAG. One reason to fail - DAG hase been
            # already added. It's safe to ignore this error. In case more serious
            # reasons, they will be caught on the "trigger_dags" step

            if not r.ok:
                reason = get_api_failure_reason(r)
                logging.error(f"Failed to add DAG {test_data['dag_id']} from test case {test_data['index']} due to \n {reason}")


def trigger_dags(suite_data, args):
    """
    Triggers all DAGs from "suite_data". If failed to trigger DAG, updates
    "suite_data" with "error" and sets "finished" to True
    """

    for run_id, test_data in suite_data.items():
        logging.info(f"Trigger DAG {test_data['dag_id']} from test case {test_data['index']} as {run_id}")
        r = requests.post(
            url=urljoin(args.api, "/api/experimental/dag_runs"),
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
        if not r.ok:
            reason = get_api_failure_reason(r)
            logging.error(f"Failed to trigger DAG {test_data['dag_id']} from test case {test_data['index']} as {run_id} due to {reason}")
            test_data["error"] = reason
            test_data["finished"] = True


def print_report(suite_data):
    exit_code = 0
    for run_id, test_data in suite_data.items():  # no need to check if "finished", because all items shoud be finished at this step
        if "error" in test_data:
            exit_code = 1
            logging.error(f"Test case {test_data['index']} that runs DAG {test_data['dag_id']} as {run_id} failed with error \n{test_data['error']}")
        else:
            logging.info(f"Test case {test_data['index']} that runs DAG {test_data['dag_id']} as {run_id} finished successfully")
    return exit_code


def run_test_conformance(args):
    """
    Runs conformance tests
    """

    # TODO: do not forget to remove args.tmp

    # Load test suite data, setup a queue to keep results
    suite_data = load_test_suite(args)
    results_queue = queue.Queue(maxsize=len(suite_data))

    # Create new dags
    create_dags(suite_data, args)                           # only reads from "suite_data"

    # Start thread to listen for status updates before
    # we trigger DAGs. "results_queue" is thread safe
    listener = get_listener_thread(
        results_queue=results_queue,
        port=args.port,
        daemon=True
    )
    listener.start()

    # Trigger all dags updating "suite_data" items with "error" and "finished"=True
    # for all DAG runs that we failed to trigger. Writing to "suite_data" is not
    # thread safe!
    trigger_dags(suite_data, args)

    # Start checker thread to evaluate received results.
    # Writes to "suite_data" which is not thread safe,
    # that's why we start thread after we triggered all DAGs.
    checker = get_checker_thread(
        suite_data=suite_data,
        results_queue=results_queue,
        daemon=False
    )
    checker.start()

    # Display spinner if --spin
    if args.spin:
        spinner = get_spinner_thread(daemon=True)
        spinner.start()

    # Wait until no unfinished items left in "suite_data"
    checker.join()

    exit_code = print_report(suite_data)

    sys.exit(exit_code)