#!/usr/bin/env python
import sys
import argparse
import uuid
from cwl_airflow.utils.mute import Mute
with Mute():  # Suppress output
    from airflow.bin.cli import scheduler
    from cwl_airflow.utils.func import export_job_file, add_run_info, update_config, export_dags, create_folders, get_demo_workflow, get_updated_args
    from cwl_airflow.utils.utils import get_workflow_output, normalize_args, exit_if_unsupported_feature


def arg_parser():
    parent_parser = argparse.ArgumentParser(add_help=False)
    general_parser = argparse.ArgumentParser(description='cwl-airflow')

    subparsers = general_parser.add_subparsers()
    subparsers.required = True

    init_parser = subparsers.add_parser('init', help="Init cwl-airflow", parents=[parent_parser])
    init_parser.set_defaults(func=run_init)
    init_parser.add_argument("-l", "--limit", dest='limit', type=int, help="Limit job concurrancy", default=10)
    init_parser.add_argument("-t", "--timeout", dest='dag_timeout', type=int, help="How long before timing out a python file import while filling the DagBag", default=30)
    init_parser.add_argument("-i", "--interval", dest='dag_interval', type=int, help="After how much time a new DAGs should be picked up from the filesystem", default=0)
    init_parser.add_argument("-r", "--refresh", dest='web_interval', type=int, help="Webserver refresh interval", default=30)
    init_parser.add_argument("-w", "--workers", dest='web_workers', type=int, help="Webserver workers refresh batch size", default=1)
    init_parser.add_argument("-p", "--threads", dest='threads', type=int, help="Max scheduler threads", default=2)

    run_parser = subparsers.add_parser('run', help="Run workflow", parents=[parent_parser])
    run_parser.set_defaults(func=run_job)
    run_parser.add_argument("-o", "--outdir", dest='output_folder', type=str, help="Output directory, default current directory", default=".")
    run_parser.add_argument("-t", "--tmp", dest='tmp_folder', type=str, help="Folder to store temporary data")
    run_parser.add_argument("-u", "--uid", dest='uid', type=str, help="Unique ID", default=str(uuid.uuid4()))
    run_parser.add_argument("-s", "--scheduler", dest='scheduler', action="store_true", help="Run schedule for single job")
    run_parser.add_argument("workflow", type=str)
    run_parser.add_argument("job", type=str)

    demo_parser = subparsers.add_parser('demo', help="Run demo workflows", parents=[parent_parser])
    demo_parser.set_defaults(func=run_demo)
    demo_parser.add_argument("-o", "--outdir", dest='output_folder', type=str, help="Output directory, default current directory", default=".")
    demo_parser.add_argument("-t", "--tmp", dest='tmp_folder', type=str, help="Folder to store temporary data")
    excl_group = demo_parser.add_mutually_exclusive_group()
    # We can't allow to set uid if we want to run all demo wokrflows. UID will be set randomly
    excl_group.add_argument("-u", "--uid", dest='uid', type=str, help="Unique ID", default=str(uuid.uuid4()))
    excl_group.add_argument("-a", "--all", dest='all', action="store_true", help="Schedule all demo workflows. Require running the separate scheduler")
    demo_parser.add_argument("-s", "--scheduler", dest='scheduler', action="store_true", help="Run schedule for single job")
    demo_parser.add_argument("workflow", type=str)

    return general_parser


def run_demo(args):
    if args.all:
        for wf in get_demo_workflow():
            run_job(get_updated_args(args, wf))
    elif args.workflow:
        try:
            run_job(get_updated_args(args, get_demo_workflow(args.workflow)[0], True, True))
        except IndexError:
            print("{} is not found in the demo workflows list".format(args.workflow))
    else:
        print("Available workflows to run:")
        for wf in get_demo_workflow():
            print("-", wf["workflow"]["name"])


def run_init(args):
    update_config(args)
    create_folders()
    export_dags()


def run_job(args):
    with Mute():
        exit_if_unsupported_feature(args.workflow)
        export_job_file(args)
    if args.scheduler:
        with Mute():
            add_run_info(args)
            scheduler(args)
        print(get_workflow_output(args.dag_id))


def main(argsl=None):
    if argsl is None:
        argsl = sys.argv[1:]
    argsl.append("")  # To avoid raising error when argsl is empty
    args, _ = arg_parser().parse_known_args(argsl)
    args = normalize_args(args, skip_list=["func", "uid", "limit", "dag_timeout", "dag_interval", "threads", "web_interval", "web_workers", "all", "scheduler"])
    args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
