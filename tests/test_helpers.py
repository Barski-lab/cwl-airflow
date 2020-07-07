import sys
import pytest
import tempfile

from os import environ, path, listdir

from shutil import rmtree
from ruamel.yaml.error import YAMLError

from cwl_airflow.utilities.helpers import (
    CleanAirflowImport,
    load_yaml,
    remove_field_from_dict
)


DATA_FOLDER = path.abspath(path.join(path.dirname(__file__), "data"))
if sys.platform == "darwin":                                           # docker has troubles of mounting /var/private on macOs
    tempfile.tempdir = "/private/tmp"


@pytest.mark.parametrize(
    "data, key, control_data",
    [
        (
            {
                "type": {
                    "type": "array",
                    "items": "string",
                    "inputBinding": {
                        "prefix": "-k"
                    }
                },
                "inputBinding": {
                    "position": 1
                },
                "doc": "-k, --key=POS1[,POS2]\nstart a key at POS1, end it at POS2 (origin 1)\n",
                "id": "linux-sort.cwl#key"
            },
            "inputBinding",
            {
                "type": {
                    "type": "array",
                    "items": "string"
                },
                "doc": "-k, --key=POS1[,POS2]\nstart a key at POS1, end it at POS2 (origin 1)\n",
                "id": "linux-sort.cwl#key"
            }
        ),
        (
            {
                "type": {
                    "type": "array",
                    "items": "string",
                    "inputBinding": {
                        "prefix": "-k"
                    }
                },
                "inputBinding": {
                    "position": 1
                },
                "doc": "-k, --key=POS1[,POS2]\nstart a key at POS1, end it at POS2 (origin 1)\n",
                "id": "linux-sort.cwl#key"
            },
            "doc",
            {
                "type": {
                    "type": "array",
                    "items": "string",
                    "inputBinding": {
                        "prefix": "-k"
                    }
                },
                "inputBinding": {
                    "position": 1
                },
                "id": "linux-sort.cwl#key"
            }
        )
    ]
)
def test_remove_field_from_dict(data, key, control_data):
    clean_data = remove_field_from_dict(data, key)
    assert all(
        control_data[key] == value
        for key, value in clean_data.items()
    ), "Failed to remove field from dictionary"


def test_load_yaml_from_file():
    location = path.join(DATA_FOLDER, "jobs", "bam-bedgraph-bigwig.json")
    data = load_yaml(location)
    assert "bam_file" in data, "Failed to load yaml (json)"


def test_load_yaml_from_string():
    location = """
        {
            "a": 1
        }
    """
    data = load_yaml(location)
    assert "a" in data, "Failed to load yaml (json)"


def test_load_yaml_from_file_should_fail():
    location = path.join(DATA_FOLDER, "jobs", "dummy.json")
    with pytest.raises(ValueError):
        data = load_yaml(location)


def test_load_yaml_from_str_should_fail():
    location = """
        {
            "a"

    """
    with pytest.raises(YAMLError):
        data = load_yaml(location)


def test_assumption_for_clean_airflow_import_if_environment_is_not_set(monkeypatch):
    temp_home = tempfile.mkdtemp()
    monkeypatch.delenv("AIRFLOW_HOME", raising=False)
    monkeypatch.delenv("AIRFLOW_CONFIG", raising=False)
    monkeypatch.setattr(
        path,
        "expanduser",
        lambda x: x.replace("~", temp_home)
    )

    import airflow

    temp_home_content = listdir(temp_home)
    rmtree(temp_home)

    assert len(temp_home_content) != 0, \
        "Possible mistake in tests, not in the tested functions"


def test_clean_airflow_import_if_environment_is_not_set(monkeypatch):
    temp_home = tempfile.mkdtemp()
    monkeypatch.delenv("AIRFLOW_HOME", raising=False)
    monkeypatch.delenv("AIRFLOW_CONFIG", raising=False)
    monkeypatch.setattr(
        path,
        "expanduser",
        lambda x: x.replace("~", temp_home)
    )

    with CleanAirflowImport():
        import airflow

    temp_home_content = listdir(temp_home)
    rmtree(temp_home)

    assert len(temp_home_content) == 0, \
        "Writing into the wrong Airflow home directory"
    assert environ.get("AIRFLOW_HOME") is None, \
        "AIRFLOW_HOME is not cleaned after exit from CleanAirflowImport"
    assert environ.get("AIRFLOW_CONFIG") is None, \
        "AIRFLOW_CONFIG is not cleaned after exit from CleanAirflowImport"


def test_assumption_for_clean_airflow_import_if_environment_is_set(monkeypatch):
    temp_home = tempfile.mkdtemp()
    temp_airflow_home = path.join(temp_home, "airflow")
    temp_airflow_cfg = path.join(temp_airflow_home, "airflow.cfg")
    monkeypatch.setenv("AIRFLOW_HOME", temp_airflow_home)
    monkeypatch.setenv("AIRFLOW_CONFIG", temp_airflow_cfg)

    import airflow

    temp_home_content = listdir(temp_home)
    rmtree(temp_home)

    assert len(temp_home_content) != 0, \
        "Possible mistake in tests, not in the tested functions"


def test_clean_airflow_import_if_environment_is_set(monkeypatch):
    temp_home = tempfile.mkdtemp()
    temp_airflow_home = path.join(temp_home, "airflow")
    temp_airflow_cfg = path.join(temp_airflow_home, "airflow.cfg")
    monkeypatch.setenv("AIRFLOW_HOME", temp_airflow_home)
    monkeypatch.setenv("AIRFLOW_CONFIG", temp_airflow_cfg)

    with CleanAirflowImport():
        import airflow

    temp_home_content = listdir(temp_home)
    rmtree(temp_home)

    assert len(temp_home_content) == 0, \
        "Writing into the wrong Airflow home directory"
    assert environ.get("AIRFLOW_HOME") == temp_airflow_home, \
        "AIRFLOW_HOME is not restored after exit from CleanAirflowImport"
    assert  environ.get("AIRFLOW_CONFIG") == temp_airflow_cfg, \
        "AIRFLOW_CONFIG is not restored after exit from CleanAirflowImport"
