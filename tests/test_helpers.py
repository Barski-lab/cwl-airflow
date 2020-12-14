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
    yield_file_content,
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
    "location, control_count",
    [
        (
            path.join(DATA_FOLDER, "jobs", "bam-bedgraph-bigwig.json"),
            11
        )
    ]
)
def test_yield_file_content(location, control_count):
    count = 0
    for _ in yield_file_content(location):
        count += 1
    assert control_count==count, \
        "Failed to read a proper number of lines from the text file"


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
    "raw_data, control_data, mtime",
    [
        (
            "hello world",
            "H4sIAEi9118C/8tIzcnJVyjPL8pJAQCFEUoNCwAAAA==",
            1607974216.711175
        ),
        (
            {"data": "hello world"},
            "H4sIAEi9118C/6tWSkksSVSyUlDKSM3JyVcozy/KSVGqBQAnYva2FwAAAA==",
            1607974216.711175
        )
    ]
)
def test_get_compressed(raw_data, control_data, mtime):
    compressed_data = get_compressed(raw_data, mtime=mtime)
    assert control_data == compressed_data, \
        "Failed to compress data"


@pytest.mark.parametrize(
    "location, control_data, reset_position, mtime",
    [
        (
            path.join(DATA_FOLDER, "jobs", "bam-bedgraph-bigwig.json"),
"H4sIAEi9118C/62NTQrCQAyF93OKkrVMW3DlAbxGiNNoB+aPJoJQevdOR0Hcm+X3vby3mq\
4e3Cji3QeGS7c20qgLJFIRXA91+oqQHanP6XDW9j6Vp0rv5uWM4zBgpFJ4woVpEluroX1u7\
wKosRwxcHro/JdRTBT5U2j1pb9z4qhNjGYzO393NUbuAAAA",
            None,
            1607974216.711175
        ),
        (
            path.join(DATA_FOLDER, "jobs", "bam-bedgraph-bigwig.json"),
"H4sIAEi9118C/5WNSwrCQBBE93OKptcyScBVDuA1mnYymoH5kW5BkNxdkxiCS2tbVe8BbE\
EXWQR7wEuIHk8G9iIWxxpKXjprm5DrQ6Vx43Smrm0pca1+oMnzIPbKCdfnvAHwMyuJos93H\
em2kHt4Hez/pZQ5+S/Q6lN/deJ4VXRmNm9wvXwe2gAAAA==",
            False,
            1607974216.711175
        )
    ]
)
def test_get_compressed_from_text_stream(location, control_data, reset_position, mtime):
    with open(location, "r") as input_stream:
        input_stream.read(20)  # change position while reading from file
        compressed_data = get_compressed(input_stream, reset_position, mtime)
    assert control_data == compressed_data, \
        "Failed to compress data"


@pytest.mark.parametrize(
    "location, control_data, reset_position, mtime",
    [
        (
            path.join(DATA_FOLDER, "jobs", "bam-bedgraph-bigwig.json"),
"H4sIAEi9118C/62NTQrCQAyF93OKkrVMW3DlAbxGiNNoB+aPJoJQevdOR0Hcm+X3vby3mq\
4e3Cji3QeGS7c20qgLJFIRXA91+oqQHanP6XDW9j6Vp0rv5uWM4zBgpFJ4woVpEluroX1u7\
wKosRwxcHro/JdRTBT5U2j1pb9z4qhNjGYzO393NUbuAAAA",
            None,
            1607974216.711175
        ),
        (
            path.join(DATA_FOLDER, "jobs", "bam-bedgraph-bigwig.json"),
"FH4sIAEi9118C/5WNSwrCQBBE93OKptcyScBVDuA1mnYymoH5kW5BkNxdkxiCS2tbVe8Bb\
EEXWQR7wEuIHk8G9iIWxxpKXjprm5DrQ6Vx43Smrm0pca1+oMnzIPbKCdfnvAHwMyuJos93\
Hem2kHt4Hez/pZQ5+S/Q6lN/deJ4VXRmNm9wvXwe2gAAAA==",
            False,
            1607974216.711175
        )
    ]
)
def test_get_compressed_from_binary_stream(location, control_data, reset_position, mtime):
    with open(location, "rb") as input_stream:
        input_stream.read(20)  # change position while reading from file
        compressed_data = get_compressed(input_stream, reset_position, mtime)
    assert control_data == compressed_data, \
        "Failed to compress data"


# tests decompression for both zlib and gzip compressed data
@pytest.mark.parametrize(
    "compressed_data, control_data, parse_as_yaml",
    [
        (
            "eNrLSM3JyVcozy/KSQEAGgsEXQ==",                                  # zlib compressed
            "hello world",
            None
        ),
        (
            "H4sIAJm3118C/8tIzcnJVyjPL8pJAQCFEUoNCwAAAA==",                  # gzip compressed
            "hello world",
            None
        ),
        (
            "eNqrVkpJLElUslJQykjNyclXKM8vyklRqgUAWl0H0Q==",                  # zlib compressed
            '{"data": "hello world"}',
            None
        ),
        (
            "H4sIALy3118C/6tWSkksSVSyUlDKSM3JyVcozy/KSVGqBQAnYva2FwAAAA==",  # gzip compressed
            '{"data": "hello world"}',
            None
        ),
        (
            "eNqrVkpJLElUslJQykjNyclXKM8vyklRqgUAWl0H0Q==",                  # zlib compressed
            '{"data": "hello world"}',
            False
        ),
        (
            "H4sIALy3118C/6tWSkksSVSyUlDKSM3JyVcozy/KSVGqBQAnYva2FwAAAA==",  # gzip compressed
            '{"data": "hello world"}',
            False
        ),
        (
            "eNqrVkpJLElUslJQykjNyclXKM8vyklRqgUAWl0H0Q==",                  # zlib compressed
            {"data": "hello world"},
            True
        ),
        (
            "H4sIADO4118C/6tWSkksSVSyUlDKSM3JyVcozy/KSVGqBQAnYva2FwAAAA==",  # gzip compressed
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
