import sys
import tempfile
import pytest

from os import path, listdir
from shutil import rmtree

from cwl_airflow.components.test.conformance import (
    load_test_suite,
    create_dags
)
from cwl_airflow.utilities.parser import parse_arguments


DATA_FOLDER = path.abspath(path.join(path.dirname(__file__), "../data"))
if sys.platform == "darwin":                                           # docker has troubles of mounting /var/private on macOs
    tempfile.tempdir = "/private/tmp"


@pytest.mark.parametrize(
    "args, control_ids",
    [
        (
            [
                "test",
                "--suite", "./conformance/test_suite_1.yaml",
                "--range", "1-3,6-8"
            ],
            [1, 2, 3, 6, 7, 8]
        ),
        (
            [
                "test",
                "--suite", "./conformance/test_suite_1.yaml",
                "--range", "100-10"
            ],
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
        )
    ]
)
def test_load_test_suite(args, control_ids):
    parsed_args = parse_arguments(args, DATA_FOLDER)
    try:
        suite_data = load_test_suite(parsed_args)
        selected_ids = [test_data["id"] for _, test_data in suite_data.items()]
    except Exception as err:
        assert False, f"Failed to run test, {err}"
    finally:
        rmtree(parsed_args.tmp)
    
    assert selected_ids == control_ids, \
        "Failed to select proper tests from --suite based on --range"
