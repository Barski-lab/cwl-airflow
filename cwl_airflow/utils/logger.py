import logging
from airflow import settings


log_format = '[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s\n%(message)s'


def reset_root_logger(quiet=None):
    for log_handler in logging.root.handlers:
        logging.root.removeHandler(log_handler)
    for log_filter in logging.root.filters:
        logging.root.removeFilter(log_filter)
    level = logging.WARN if quiet else settings.LOGGING_LEVEL
    logging.basicConfig(level=level, format=log_format)
