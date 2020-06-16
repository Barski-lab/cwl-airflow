import argparse

from os import environ, getcwd

from cwl_airflow.utilities.helpers import (
    get_version,
    get_absolute_path,
    CleanAirflowImport
)

from cwl_airflow.components.api.server import run_api_server
from cwl_airflow.components.init.config import run_init_config

with CleanAirflowImport():
    from airflow.configuration import (
        get_airflow_home,
        get_airflow_config
    )


def get_normalized_args(args, skip_list=None, cwd=None):
    """
    Converts all relative path arguments to absolute
    ones relatively to the cwd or current working directory.
    Skipped arguments and None will be returned unchanged.
    """

    cwd = getcwd() if cwd is None else cwd
    skip_list = [] if skip_list is None else skip_list

    normalized_args = {}
    for key, value in args.__dict__.items():
        if key not in skip_list and value is not None:
            if isinstance(value, list):
                for v in value:
                    normalized_args.setdefault(key, []).append(
                        get_absolute_path(v, cwd)
                    )
            else:
                normalized_args[key] = get_absolute_path(value, cwd)
        else:
            normalized_args[key] = value
    return argparse.Namespace(**normalized_args)


def get_parser():
    """
    Defines arguments for parser. Inlcudes two subparsers for
    api server and init components.
    """

    parent_parser = argparse.ArgumentParser(add_help=False)
    general_parser = argparse.ArgumentParser(
        description="CWL-Airflow: a lightweight pipeline manager \
            supporting Common Workflow Language"
    )
    subparsers = general_parser.add_subparsers()
    subparsers.required = True

    general_parser.add_argument(                       
        "--version",
        action="version",
        version=get_version(),
        help="Print current version and exit"
    )

    # API
    api_parser = subparsers.add_parser(
        "api",
        parents=[parent_parser],
        help="Run API server"
    )
    api_parser.set_defaults(func=run_api_server)
    api_parser.add_argument(
        "--port", 
        type=int,
        default=8081,
        help="Set port to run API server. Default: 8081",
    )
    api_parser.add_argument(
        "--host", 
        type=str,
        default="127.0.0.1",
        help="Set host to run API server. Default: 127.0.0.1"
    )

    # Init
    init_parser = subparsers.add_parser(
        "init",
        parents=[parent_parser],
        help="Run initial configuration"
    )
    init_parser.set_defaults(func=run_init_config)
    init_parser.add_argument(
        "--home", 
        type=str,
        default=get_airflow_home(),
        help="Set path to Airflow home directory. \
            Default: first try AIRFLOW_HOME then '~/airflow'"
    )
    init_parser.add_argument(
        "--config", 
        type=str,
        help="Set path to Airflow configuration file. \
            Default: first try AIRFLOW_CONFIG then '[airflow home]/airflow.cfg'"
    )

    return general_parser


def assert_and_fix_args_for_init(args):
    """
    Asserts, fixes and sets parameters from init parser.
    """
    
    if args.config is None:
        args.config = get_airflow_config(args.home)


def assert_and_fix_args(args):
    """
    Should be used to assert and fix parameters.
    Also can be used to set default values for not
    set parameters in case the later onec depends on other
    parameters that should be first parsed by argparser
    """

    if args.func == run_init_config:
        assert_and_fix_args_for_init(args)
    else:
        pass  # TODO: once needed, put here something like assert_and_fix_args_for_api


def parse_arguments(argsl, cwd=None):
    """
    Parses provided through argsl arguments.
    All relative paths will be resolved relative
    to the cwd or current working directory.
    Set argsl to [""] if empty to prevent argparse from failing
    """

    cwd = getcwd() if cwd is None else cwd
    argsl = argsl + [""] if len(argsl) == 0 else argsl
    
    args, _ = get_parser().parse_known_args(argsl)
    args = get_normalized_args(
        args,
        ["func", "port", "host"],
        cwd
    )
    assert_and_fix_args(args)
    return args