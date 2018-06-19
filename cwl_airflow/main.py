#!/usr/bin/env python
import os
import sys
import argparse
from typing import Text
import cwltool.errors


RUN_PARAM_FILE = "run_param.tmp"
NULL_FDS = []
BACKUP_FDS = []


def suppress_stdout():
    global NULL_FDS
    NULL_FDS = [os.open(os.devnull, os.O_RDWR) for x in range(2)]
    global BACKUP_FDS
    BACKUP_FDS = os.dup(1), os.dup(2)
    os.dup2(NULL_FDS[0], 1)
    os.dup2(NULL_FDS[1], 2)


def restore_stdout():
    os.dup2(BACKUP_FDS[0], 1)
    os.dup2(BACKUP_FDS[1], 2)
    os.close(NULL_FDS[0])
    os.close(NULL_FDS[1])


# suppress_stdout()
from airflow.bin.cli import backfill
from airflow import configuration
from cwl_airflow.utils.utils import (create_backup_args,
                                     remove_backup_args,
                                     read_backup_args,
                                     print_workflow_output,
                                     update_config,
                                     copy_cwl_dag,
                                     create_folders)
from cwl_airflow.utils.func import make_dag
# restore_stdout()


def arg_parser():
    parent_parser = argparse.ArgumentParser(add_help=False)

    general_parser = argparse.ArgumentParser(description='cwl-airflow')
    subparsers = general_parser.add_subparsers()
    subparsers.required = True
    init_parser = subparsers.add_parser('init', help="Init cwl-airflow", parents=[parent_parser])
    run_parser = subparsers.add_parser('run',  help="Run workflow", parents=[parent_parser])

    init_parser.set_defaults(func=run_init)

    run_parser.add_argument("--outdir", help="Output folder to save results")
    run_parser.add_argument("--tmp-folder", help="Temp folder to store data between execution of airflow tasks/steps")
    run_parser.add_argument("--tmpdir-prefix", help="Path prefix for temporary directories")
    run_parser.add_argument("--tmp-outdir-prefix", help="Path prefix for intermediate output directories")
    run_parser.add_argument("--quiet", action="store_true", help="Print only workflow execultion results")
    run_parser.add_argument("workflow", type=Text)
    run_parser.add_argument("job", type=Text)
    # TODO remove or make it more clear WTF this argument means?
    run_parser.add_argument("--ignore-def-outdir", action="store_true",
                            help="Disable default output directory to be set to current directory. Use OUTPUT_FOLDER from Airflow configuration file instead")

    run_parser.set_defaults(func=run_job)

    return general_parser


def run_init (**kwargs):
    update_config(configuration)
    with open(configuration.AIRFLOW_CONFIG, 'w') as cfg_file:
        configuration.conf.write(cfg_file)
    copy_cwl_dag(configuration)   # raise if not enough permissions to write file
    create_folders(configuration)  # raise if not enough permissions to create a folder


def run_job (**kwargs):
    create_backup_args(kwargs, RUN_PARAM_FILE)
    try:
        args = argparse.Namespace (**kwargs)
        if args.quiet:
            suppress_stdout()
        backfill(args)
        if args.quiet:
            restore_stdout()
        print_workflow_output (args)
        remove_backup_args(RUN_PARAM_FILE)
    except KeyboardInterrupt:
        remove_backup_args(RUN_PARAM_FILE)
    except Exception:
        remove_backup_args(RUN_PARAM_FILE)
        raise


def main(argsl=None):
    if argsl is None:
        argsl = sys.argv[1:]
    args, _ = arg_parser().parse_known_args(argsl)
    args.func(**args.__dict__)


try:
    make_dag(read_backup_args(RUN_PARAM_FILE))
except cwltool.errors.UnsupportedRequirement as feature_ex:
    print(feature_ex)
    remove_backup_args(RUN_PARAM_FILE)
    sys.exit(33)
except Exception as ex:
    pass


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
