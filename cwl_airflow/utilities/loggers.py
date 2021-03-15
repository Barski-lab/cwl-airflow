import logging
from cwl_airflow.utilities.cwl import conf_get


def setup_cwl_logger(ti, level=None):
    """
    Sets logging level of cwltool logger to correspond LOGGING_LEVEL
    from airflow.cfg. Configures handler based on the task instance
    to redirect output to the proper file. Suppresses those loggers
    from cwltool or related packages that spam.
    Note: maybe we will need to remove StreamHandler <stderr> handler
    from cwltool logger in case we see undesired outputs in the airflow
    logs but not in the separate files.
    """

    level = conf_get("core", "LOGGING_LEVEL", "INFO").upper() if level is None else level
    cwl_logger = logging.getLogger("cwltool")
    for handler in cwl_logger.handlers:
        try:
            handler.set_context(ti)
        except AttributeError:
            pass
    cwl_logger.setLevel(level)

    less_verbose(
        loggers=["rdflib.term", "salad", "requests", "urllib3"],
        level="ERROR"
    )


def less_verbose(loggers=None, level=None):
    """
    For a list of loggers sets desired level
    """

    loggers = ["cwltool", "rdflib.term", "salad", "requests", "urllib3"] if loggers is None else loggers
    level = "FATAL" if level is None else level

    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
