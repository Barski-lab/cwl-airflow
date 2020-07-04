import os
import logging
import uuid

from queue import Queue
from collections import OrderedDict

from airflow.settings import DAGS_FOLDER

from cwl_airflow.utilities.helpers import (
    load_yaml,
    get_dir,
    get_absolute_path,
    get_rootname
)
from cwl_airflow.utilities.airflow import DAG_TEMPLATE


def load_test_suite(args):
    """
    Loads tests from the provided --suite file.
    Selects tests based on the indices from --range.
    Updates all tool and job locations to be absolute.
    Adds run_id's as keys for easy access and proper
    test identification when test is run.
    """

    suite_data = load_yaml(args.suite)
    suite_dir = os.path.dirname(args.suite)
    suite_data_filtered = OrderedDict()          # use OrderedDict just to keep it similar to suite_data
    for i in args.range:
        test_data = suite_data[i]
        test_data.update({
            "job":  get_absolute_path(test_data["job"], suite_dir),
            "tool": get_absolute_path(test_data["tool"], suite_dir),
        })
        run_id = str(uuid.uuid4())
        suite_data_filtered[run_id] = test_data
    return suite_data_filtered


def create_dags(suite_data, dags_folder=None):
    """
    Iterates over suite_data and exports DAG files into dags_folder.
    If file with the same name has already been exported, skip it.
    If dags_folder is not set, use DAGS_FOLDER from airflow.settings

    TODO: maybe I will need to copy packed cwl file into the dags_folder too.
    """

    if dags_folder is None:
        dags_folder = get_dir(DAGS_FOLDER)
    else:
        dags_folder = get_dir(dags_folder)

    for test_data in suite_data.values():
        tool_location = test_data["tool"]
        dag_id = get_rootname(tool_location)
        dag_location = os.path.join(
            dags_folder,
            dag_id + ".py"
        )
        if not os.path.isfile(dag_location):
            with open(dag_location, 'w') as output_stream:
                output_stream.write(
                    DAG_TEMPLATE.format(
                        tool_location,
                        dag_id
                    )
                )


def run_test_conformance(args):
    """
    Runs conformance tests
    """

    # Load test suite data, setup a queue for tests
    suite_data = load_test_suite(args)
    suite_queue = Queue(maxsize=len(suite_data))

    # Create new dags
    create_dags(suite_data)

    # Start status update listener
    listener = get_listener_thread(queue=queue, port=args.port, daemon=True)
    listener.start()

    # Start checker thread
    checker = get_checker_thread(data=data_dict, daemon=False)
    checker.start()

    # Trigger all dags
    trigger_dags(data_dict, args)

    # Display spinner if  --spin
    if args.spin:
        spinner = get_spinner_thread()
        spinner.start()

    # Wait until all triggered dags return results
    checker.join()

    if any(item.get("error", None) for item in data_dict.values()):
        sys.exit(1)