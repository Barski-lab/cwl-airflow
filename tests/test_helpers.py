import sys
import pytest
import tempfile
import zlib
import binascii

from os import environ, path, listdir

from shutil import rmtree
from ruamel.yaml.error import YAMLError

from cwl_airflow.utilities.helpers import (
    CleanAirflowImport,
    load_yaml,
    remove_field_from_dict,
    get_compressed,
    get_uncompressed,
    get_md5_sum
)


DATA_FOLDER = path.abspath(path.join(path.dirname(__file__), "data"))
if sys.platform == "darwin":                                           # docker has troubles of mounting /var/private on macOs
    tempfile.tempdir = "/private/tmp"


@pytest.mark.parametrize(
    "location, control_md5sum",
    [
        (
            path.join(DATA_FOLDER, "jobs", "bam-bedgraph-bigwig.json"),
            "7160a22c6dd7e7caa9be5de3e4978400"
        ),
        (
            "content of a file",
            "80ecb1219dd7655292e85ac40fce6781"
        )
    ]
)
def test_get_md5_sum(location, control_md5sum):
    md5sum = get_md5_sum(location)
    assert control_md5sum==md5sum, \
        "Failed to calculate md5 sum"


@pytest.mark.parametrize(
    "raw_data, control_data",
    [
        (
            "hello world",
            "eNrLSM3JyVcozy/KSQEAGgsEXQ=="
        ),
        (
            {"data": "hello world"},
            "eNqrVkpJLElUslJQykjNyclXKM8vyklRqgUAWl0H0Q=="
        )
    ]
)
def test_get_compressed(raw_data, control_data):
    compressed_data = get_compressed(raw_data)
    assert control_data == compressed_data, \
        "Failed to compress data"


@pytest.mark.parametrize(
    "location, control_data, reset_position",
    [
        (
            path.join(DATA_FOLDER, "jobs", "bam-bedgraph-bigwig.json"),
"eNqtjU0KwkAMhfdzipK1TFtw5QG8RojTaAfmjyaCUHr3TkdB3Jvl9728t5quHtwo4t0Hh\
ku3NtKoCyRSEVwPdfqKkB2pz+lw1vY+ladK7+bljOMwYKRSeMKFaRJbq6F9bu8CqLEcMXB\
66PyXUUwU+VNo9aW/c+KoTYxmMzssgkGR",
            None
        ),
        (
            path.join(DATA_FOLDER, "jobs", "bam-bedgraph-bigwig.json"),
"eNqVjUsKwkAQRPdziqbXMknAVQ7gNZp2MpqB+ZFuQZDcXZMYgktrW1XvAWxBF1kEe8BLiB5P\
BvYiFscaSl46a5uQ60OlceN0pq5tKXGtfqDJ8yD2ygnX57wB8DMriaLPdx3ptpB7eB3s/6WUO\
fkv0OpTf3XieFV0ZjZvaoo8Og==",
            False
        )
    ]
)
def test_get_compressed_from_text_stream(location, control_data, reset_position):
    with open(location, "r") as input_stream:
        input_stream.read(20)  # change position while reading from file
        compressed_data = get_compressed(input_stream, reset_position)
    assert control_data == compressed_data, \
        "Failed to compress data"


@pytest.mark.parametrize(
    "location, control_data, reset_position",
    [
        (
            path.join(DATA_FOLDER, "jobs", "bam-bedgraph-bigwig.json"),
"eNqtjU0KwkAMhfdzipK1TFtw5QG8RojTaAfmjyaCUHr3TkdB3Jvl9728t5quHtwo4t0Hh\
ku3NtKoCyRSEVwPdfqKkB2pz+lw1vY+ladK7+bljOMwYKRSeMKFaRJbq6F9bu8CqLEcMXB\
66PyXUUwU+VNo9aW/c+KoTYxmMzssgkGR",
            None
        ),
        (
            path.join(DATA_FOLDER, "jobs", "bam-bedgraph-bigwig.json"),
"eNqVjUsKwkAQRPdziqbXMknAVQ7gNZp2MpqB+ZFuQZDcXZMYgktrW1XvAWxBF1kEe8BLiB5P\
BvYiFscaSl46a5uQ60OlceN0pq5tKXGtfqDJ8yD2ygnX57wB8DMriaLPdx3ptpB7eB3s/6WUO\
fkv0OpTf3XieFV0ZjZvaoo8Og==",
            False
        )
    ]
)
def test_get_compressed_from_binary_stream(location, control_data, reset_position):
    with open(location, "rb") as input_stream:
        input_stream.read(20)  # change position while reading from file
        compressed_data = get_compressed(input_stream, reset_position)
    assert control_data == compressed_data, \
        "Failed to compress data"


@pytest.mark.parametrize(
    "compressed_data, control_data, parse_as_yaml",
    [
        (
            "eNrLSM3JyVcozy/KSQEAGgsEXQ==",
            "hello world",
            None
        ),
        (
            "eNqrVkpJLElUslJQykjNyclXKM8vyklRqgUAWl0H0Q==",
            '{"data": "hello world"}',
            None
        ),
        (
            "eNqrVkpJLElUslJQykjNyclXKM8vyklRqgUAWl0H0Q==",
            '{"data": "hello world"}',
            False
        ),
        (
            "eNqrVkpJLElUslJQykjNyclXKM8vyklRqgUAWl0H0Q==",
            {"data": "hello world"},
            True
        )
    ]
)
def test_get_uncompressed(compressed_data, control_data, parse_as_yaml):
    uncompressed_data = get_uncompressed(compressed_data, parse_as_yaml)
    assert control_data == uncompressed_data, \
        "Failed to uncompress data"


@pytest.mark.parametrize(
    "compressed_data, control_data, parse_as_yaml",
    [
        (
            "random string",
            '{"data": "hello world"}',
            None
        ),
        (
            "~/workflows/bam-bedgraph-bigwig.cwl",
            "",
            None
        ),
        (
            "eNrLSM3JyVcozy/KSQEAGgsEXQ==",
            "hello world",
            True
        ),
        (
            "eNqrVk+sBQADpAGB",
            "{'a}",
            True
        )
    ]
)
def test_get_uncompressed_should_fail(compressed_data, control_data, parse_as_yaml):
    with pytest.raises((zlib.error, binascii.Error, ValueError, YAMLError)):
        uncompressed_data = get_uncompressed(compressed_data, parse_as_yaml)


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



@pytest.mark.parametrize(
    "location",
    [
        (
            '{"a"'
        ),
        (
            "text"
        )
    ]
)
def test_load_yaml_from_str_should_fail(location):
    with pytest.raises((YAMLError, ValueError)):
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
