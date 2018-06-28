#!/usr/bin/env python
import sys
import argparse
import uuid
from cwl_airflow.utils.mute import suppress_stdout, restore_stdout
suppress_stdout()
# Suppress output
from airflow.bin.cli import scheduler
from cwl_airflow.utils.func import export_job_file, update_args, update_config, export_dags, create_folders
from cwl_airflow.utils.utils import get_workflow_output, normalize_args, exit_if_unsupported_feature
# Restore output
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
    run_parser.add_argument("-o", "--output", dest='output_folder', type=str, help="Output folder", default=".")
    run_parser.add_argument("-t", "--tmp", dest='tmp_folder', type=str, help="Temporary folder")
    run_parser.add_argument("-u", "--uid", dest='uid', type=str, help="Unique ID", default=str(uuid.uuid4()))
    run_parser.add_argument("workflow", type=str)
    run_parser.add_argument("job", type=str)

    return general_parser


def run_init(args):
    update_config()
    create_folders()
    export_dags()


def run_job(args):
    suppress_stdout()
    exit_if_unsupported_feature(args.workflow)
    export_job_file(args)
    update_args(args)
    scheduler(args)
    restore_stdout()
    print(get_workflow_output(args.dag_id))


def main(argsl=None):
    if argsl is None:
        argsl = sys.argv[1:]
    argsl.append("")  # To avoid raising error when argsl is empty
    args, _ = arg_parser().parse_known_args(argsl)
    args = normalize_args(args, skip_list=["func", "uid"])
    args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
