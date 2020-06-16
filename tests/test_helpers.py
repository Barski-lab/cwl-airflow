import sys

from os import environ, path, listdir
from tempfile import mkdtemp
from shutil import rmtree

from cwl_airflow.utilities.helpers import (
    CleanAirflowImport
)


def test_assumption_for_clean_airflow_import_if_environment_is_not_set(monkeypatch):
    temp_home = mkdtemp()
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
    temp_home = mkdtemp()
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
    temp_home = mkdtemp()
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
    temp_home = mkdtemp()
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
