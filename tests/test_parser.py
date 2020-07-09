import sys
import pytest
import tempfile

from os import environ, path
from shutil import rmtree

from cwl_airflow.utilities.parser import parse_arguments
from cwl_airflow.utilities.helpers import get_absolute_path


DATA_FOLDER = path.abspath(path.join(path.dirname(__file__), "data"))
if sys.platform == "darwin":                                           # docker has troubles of mounting /var/private on macOs
    tempfile.tempdir = "/private/tmp"


@pytest.mark.parametrize(
    "args, control",
    [
        (
            [
                "test",
                "--suite", "./conformance/test_suite_1.yaml"
            ],
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
        ),
        (
            [
                "test",
                "--suite", "./conformance/test_suite_1.yaml",
                "--range", "1-3,6-8"
            ],
            [0, 1, 2, 5, 6, 7]
        ),
        (
            [
                "test",
                "--suite", "./conformance/test_suite_1.yaml",
                "--range", "1-3,6-8,9"
            ],
            [0, 1, 2, 5, 6, 7, 8]
        ),
        (
            [
                "test",
                "--suite", "./conformance/test_suite_1.yaml",
                "--range", "1-3, 6-8, 9"
            ],
            [0, 1, 2, 5, 6, 7, 8]
        ),
        (
            [
                "test",
                "--suite", "./conformance/test_suite_1.yaml",
                "--range", "1-3, 6-8, 9, 9, 9"
            ],
            [0, 1, 2, 5, 6, 7, 8]
        ),
        (
            [
                "test",
                "--suite", "./conformance/test_suite_1.yaml",
                "--range", "1-2, 9, 9, 9"
            ],
            [0, 1, 8]
        ),
        (
            [
                "test",
                "--suite", "./conformance/test_suite_1.yaml",
                "--range", "3-2, 9, 9, 9"
            ],
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
        ),
        (
            [
                "test",
                "--suite", "./conformance/test_suite_1.yaml",
                "--range", "16"
            ],
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
        ),
        (
            [
                "test",
                "--suite", "./conformance/test_suite_1.yaml",
                "--range", "-11"
            ],
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
        ),
        (
            [
                "test",
                "--suite", "./conformance/test_suite_1.yaml",
                "--range", "11-"
            ],
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
        ),
        (
            [
                "test",
                "--suite", "./conformance/test_suite_1.yaml",
                "--range", "1-100"
            ],
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
        ),
        (
            [
                "test",
                "--suite", "./conformance/test_suite_1.yaml",
                "--range", "100-110"
            ],
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
        )
    ]
)
def test_parse_arguments_for_making_list_from_range_in_test_subparser(args, control):
    result_args = parse_arguments(args, DATA_FOLDER)
    rmtree(result_args.tmp)

    assert result_args.range == control


def test_parse_arguments_for_init_with_both_params_if_environment_is_not_set(monkeypatch):
    temp_home = tempfile.mkdtemp()
    monkeypatch.delenv("AIRFLOW_HOME", raising=False)
    monkeypatch.delenv("AIRFLOW_CONFIG", raising=False)
    monkeypatch.setattr(
        path,
        "expanduser",
        lambda x: x.replace("~", temp_home)
    )
    
    control_airflow_home = path.join(temp_home, "not_default_anymore", "airflow")
    control_airflow_cfg = path.join(control_airflow_home, "airflow.cfg")
    
    input_args = [
        "init",
        "--home", control_airflow_home,
        "--config", control_airflow_cfg
    ]

    result_args = parse_arguments(input_args, temp_home)
    rmtree(temp_home)

    assert result_args.home == control_airflow_home, \
        "Failed to parse --home"
    assert result_args.config == control_airflow_cfg, \
        "Failed to parse --config"


def test_parse_arguments_for_init_with_both_params_if_environment_is_set(monkeypatch):
    temp_home = tempfile.mkdtemp()
    temp_airflow_home = path.join(temp_home, "original", "airflow")
    temp_airflow_cfg = path.join(temp_airflow_home, "airflow.cfg")
    monkeypatch.setenv("AIRFLOW_HOME", temp_airflow_home)
    monkeypatch.setenv("AIRFLOW_CONFIG", temp_airflow_cfg)
    monkeypatch.setattr(
        path,
        "expanduser",
        lambda x: x.replace("~", temp_home)
    )
    
    control_airflow_home = path.join(temp_home, "not_default_anymore", "airflow")
    control_airflow_cfg = path.join(control_airflow_home, "airflow.cfg")
    
    input_args = [
        "init",
        "--home", control_airflow_home,
        "--config", control_airflow_cfg
    ]

    result_args = parse_arguments(input_args, temp_home)
    rmtree(temp_home)

    assert result_args.home == control_airflow_home, \
        "Failed to parse --home"
    assert result_args.config == control_airflow_cfg, \
        "Failed to parse --config"


def test_parse_arguments_for_init_with_relative_path_for_both_params_if_environment_is_not_set(monkeypatch):
    temp_home = tempfile.mkdtemp()
    monkeypatch.delenv("AIRFLOW_HOME", raising=False)
    monkeypatch.delenv("AIRFLOW_CONFIG", raising=False)
    monkeypatch.setattr(
        path,
        "expanduser",
        lambda x: x.replace("~", temp_home)
    )
    
    input_airflow_home = "./not_default_anymore/airflow"
    input_airflow_cfg = "./not_default_anymore/airflow/airflow.cfg"
    
    control_airflow_home = get_absolute_path(input_airflow_home, temp_home)
    control_airflow_cfg = get_absolute_path(input_airflow_cfg, temp_home)

    input_args = [
        "init",
        "--home", input_airflow_home,
        "--config", input_airflow_cfg
    ]

    result_args = parse_arguments(input_args, temp_home)
    rmtree(temp_home)

    assert result_args.home == control_airflow_home, \
        "Failed to parse --home"
    assert result_args.config == control_airflow_cfg, \
        "Failed to parse --config"


def test_parse_arguments_for_init_with_defaults_if_environment_is_not_set(monkeypatch):
    temp_home = tempfile.mkdtemp()
    monkeypatch.delenv("AIRFLOW_HOME", raising=False)
    monkeypatch.delenv("AIRFLOW_CONFIG", raising=False)
    monkeypatch.setattr(
        path,
        "expanduser",
        lambda x: x.replace("~", temp_home)
    )
    
    control_airflow_home = path.join(temp_home, "airflow")
    control_airflow_cfg = path.join(control_airflow_home, "airflow.cfg")
    
    input_args = ["init"]

    result_args = parse_arguments(input_args, temp_home)
    rmtree(temp_home)

    assert result_args.home == control_airflow_home, \
        "Failed to set default for --home. \
         Check if get_airflow_home or get_airflow_config \
         from airflow.configuration were not changed"
    assert result_args.config == control_airflow_cfg, \
        "Failed to set default for --config \
         Check if get_airflow_home or get_airflow_config \
         from airflow.configuration were not changed"


def test_parse_arguments_for_init_with_defaults_if_environment_is_set(monkeypatch):
    temp_home = tempfile.mkdtemp()
    temp_airflow_home = path.join(temp_home, "original", "airflow")
    temp_airflow_cfg = path.join(temp_airflow_home, "airflow.cfg")
    monkeypatch.setenv("AIRFLOW_HOME", temp_airflow_home)
    monkeypatch.setenv("AIRFLOW_CONFIG", temp_airflow_cfg)
    monkeypatch.setattr(
        path,
        "expanduser",
        lambda x: x.replace("~", temp_home)
    )
    
    input_args = ["init"]

    result_args = parse_arguments(input_args, temp_home)
    rmtree(temp_home)

    assert result_args.home == temp_airflow_home, \
        "Failed to set default for --home. \
         Check if get_airflow_home or get_airflow_config \
         from airflow.configuration were not changed"
    assert result_args.config == temp_airflow_cfg, \
        "Failed to set default for --config \
         Check if get_airflow_home or get_airflow_config \
         from airflow.configuration were not changed"