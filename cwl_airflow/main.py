#!/usr/bin/env python
import os
import sys
import argparse
import ruamel.yaml as yaml
from json import dumps
from typing import Text


NULL_FDS, BACKUP_FDS = [], []


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


suppress_stdout()
from airflow.bin.cli import scheduler, get_dag, CLIFactory
from airflow import configuration
from cwl_airflow.utils.utils import (update_config,
                                     copy_cwl_dag,
                                     create_folders,
                                     get_workflow_output)
from airflow.configuration import conf
from cwl_airflow.utils.utils import export_to_file
from cwl_airflow.utils.utils import gen_dag_id
restore_stdout()


def arg_parser():
    parent_parser = argparse.ArgumentParser(add_help=False)
    general_parser = argparse.ArgumentParser(description='cwl-airflow')

    subparsers = general_parser.add_subparsers()
    subparsers.required = True

    init_parser = subparsers.add_parser('init', help="Init cwl-airflow", parents=[parent_parser])
    init_parser.set_defaults(func=run_init)

    run_parser = subparsers.add_parser('run', help="Run workflow", parents=[parent_parser])
    run_parser.set_defaults(func=run_job)
    run_parser.add_argument("workflow", type=Text)
    run_parser.add_argument("job", type=Text)

    return general_parser


def run_init(**kwargs):
    update_config(configuration)
    with open(configuration.AIRFLOW_CONFIG, 'w') as cfg_file:
        configuration.conf.write(cfg_file)
    copy_cwl_dag(configuration)
    create_folders(configuration)


def run_job(**kwargs):
    suppress_stdout()
    kwargs.update({arg_name: arg_value.default for arg_name, arg_value in CLIFactory.args.items()
                   if arg_name in CLIFactory.subparsers_dict['scheduler']['args']})
    args = argparse.Namespace (**kwargs)
    with open(args.job, 'r') as input_stream:
        job_entry = yaml.safe_load(input_stream)
        job_entry['workflow'] = os.path.abspath(args.workflow)
        output_file = os.path.join(conf.get('biowardrobe', 'jobs'), os.path.basename(args.job))
        export_to_file(output_file, dumps(job_entry, indent=4))
        args.dag_id = gen_dag_id(kwargs["workflow"], output_file)
    args.num_runs = len(get_dag(args).tasks) + 3  # Need at least 2 more times to reads the DAG file to set the status for DagRun
    scheduler(args)
    restore_stdout()
    print(get_workflow_output(args.dag_id))


def main(argsl=None):
    if argsl is None:
        argsl = sys.argv[1:]
    args, _ = arg_parser().parse_known_args(argsl)
    args.func(**args.__dict__)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
