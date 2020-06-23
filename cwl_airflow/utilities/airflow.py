from airflow.configuration import conf
from airflow.exceptions import AirflowConfigException


def conf_get(section, key, default):
    """
    Return value from AirflowConfigParser object.
    If section or key is absent, return default
    """

    try:
        return conf.get(section, key)
    except AirflowConfigException:
        return default
