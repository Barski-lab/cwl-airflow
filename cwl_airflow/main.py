#!/usr/bin/env python
import sys
import os
import argparse
import uuid
import logging
from cwl_airflow.utils.mute import Mute
with Mute():  # Suppress output
    from airflow.settings import AIRFLOW_HOME
    from cwl_airflow.utils.logger import reset_root_logger
    from airflow.bin.cli import scheduler, webserver, initdb
    from cwl_airflow.utils.func import (export_job_file,
                                        add_run_info,
                                        update_config,
                                        export_dags,
                                        create_folders,
                                        get_demo_workflow,
                                        get_updated_args,
                                        start_background_scheduler,
                                        get_airflow_default_args,
                                        clean_jobs_folder,
                                        get_webserver_url,
                                        asset_conf)
    from cwl_airflow.utils.utils import (get_workflow_output,
                                         normalize_args,
                                         exit_if_unsupported_feature,
                                         conf_get_default)


def arg_parser():
    parent_parser = argparse.ArgumentParser(add_help=False)
    general_parser = argparse.ArgumentParser(description='cwl-airflow')

    general_parser.add_argument("-q", "--quiet", dest='quiet', action="store_true", help="Suppress all output except warnings and errors")

    subparsers = general_parser.add_subparsers()
    subparsers.required = True


    init_parser = subparsers.add_parser('init', help="Init cwl-airflow", parents=[parent_parser])
    init_parser.set_defaults(func=run_init)
    init_parser.add_argument("-l", "--limit",    dest='limit', type=int, help="Limit job concurrancy",
                             default=conf_get_default("cwl", "limit", 10))
    init_parser.add_argument("-j", "--jobs",     dest='jobs', type=str, help="Jobs folder. Default: ~/airflow/jobs",
                             default=conf_get_default("cwl", "jobs", os.path.join(AIRFLOW_HOME, 'jobs')))
    init_parser.add_argument("-t", "--timeout",  dest='dag_timeout', type=int, help="How long before timing out a python file import while filling the DagBag",
                             default=conf_get_default("core", "dagbag_import_timeout", 30))
    init_parser.add_argument("-r", "--refresh",  dest='web_interval', type=int, help="Webserver workers refresh interval, seconds",
                             default=conf_get_default("webserver", "worker_refresh_interval", 30))
    init_parser.add_argument("-w", "--workers",  dest='web_workers', type=int, help="Webserver workers refresh batch size",
                             default=conf_get_default("webserver", "worker_refresh_batch_size", 1))
    init_parser.add_argument("-p", "--threads",  dest='threads', type=int, help="Max Airflow Scheduler threads",
                             default=conf_get_default("scheduler", "max_threads", 2))


    submit_parser = subparsers.add_parser('submit', help="Submit custom workflow", parents=[parent_parser])
    submit_parser.set_defaults(func=submit_job)
    submit_parser.add_argument("-o", "--outdir", dest='output_folder', type=str, help="Output directory. Default: ./", default=".")
    submit_parser.add_argument("-t", "--tmp", dest='tmp_folder', type=str, help="Folder to store temporary data. Default: /tmp")
    submit_parser.add_argument("-u", "--uid", dest='uid', type=str, help="Experiment unique ID. Default: random uuid", default=str(uuid.uuid4()))
    submit_parser.add_argument("-r", "--run", dest='run', action="store_true", help="Run workflow with Airflow Scheduler")
    submit_parser.add_argument("workflow", type=str, help="Workflow file path")
    submit_parser.add_argument("job", type=str, help="Job file path")


    demo_parser = subparsers.add_parser('demo', help="Run demo workflows", parents=[parent_parser])
    demo_parser.set_defaults(func=run_demo)
    demo_parser.add_argument("-o", "--outdir", dest='output_folder', type=str, help="Output directory. Default: ./", default=".")
    demo_parser.add_argument("-t", "--tmp", dest='tmp_folder', type=str, help="Folder to store temporary data. Default: /tmp")
    demo_parser.add_argument("-u", "--uid", dest='uid', type=str, help="Experiment's unique ID; ignored with -a/-l arguments. Default: random uuid", default=str(uuid.uuid4()))
    demo_parser.add_argument("workflow", type=str, help="Demo workflow name from the list")


    excl_group = demo_parser.add_mutually_exclusive_group()
    excl_group.add_argument("-a", "--auto", dest='auto', action="store_true", help="Run all demo workflows with Airflow Webserver & Scheduler")
    excl_group.add_argument("-m", "--manual", dest='manual', action="store_true", help="Submit all demo workflows. Requires Airflow Webserver & Scheduler to be run separately")
    excl_group.add_argument("-l", "--list", dest='list', action="store_true", help="List demo workflows")

    return general_parser


def run_demo_auto(args):
    run_demo_manual(args)
    start_background_scheduler()
    logging.info("Run Airflow Webserver in background\n- to open webserver follow the link {}".format(get_webserver_url()))
    with Mute():
        webserver(get_airflow_default_args("webserver"))


def run_demo_manual(args):
    clean_jobs_folder()
    workflows = get_demo_workflow()
    for idx, wf in enumerate(workflows):
        logging.info("Process demo workflow {}/{}".format(idx+1, len(workflows)))
        submit_job(get_updated_args(args, wf))


def run_demo(args):
    asset_conf()
    if args.auto:
        run_demo_auto(args)
    elif args.manual:
        run_demo_manual(args)
        logging.info("To process submitted workflows run Airflow Scheduler separately")
    elif args.list:
        print("Available demo workflows:")
        for wf in get_demo_workflow():
            print("-", wf["workflow"]["name"])
    elif args.workflow:
        try:
            submit_job(get_updated_args(args, get_demo_workflow(args.workflow)[0], keep_uid=True, keep_output_folder=True))
        except IndexError:
            logging.warning("{} is not found in the demo workflows list".format(args.workflow))
        logging.info("To process submitted workflows run Airflow Scheduler separately")
    else:
        arg_parser().parse_known_args(["demo", "--help"])


def run_init(args):
    asset_conf("init")
    logging.info("Init cwl-airflow")
    update_config(args)
    create_folders()
    export_dags()
    logging.info("Init Airflow DB")
    with Mute():
        initdb(argparse.Namespace())


def submit_job(args):
    asset_conf()
    logging.info("Load workflow\n- workflow: {workflow}\n- job:      {job}\n- uid:      {uid}".format(**vars(args)))
    exit_if_unsupported_feature(args.workflow)
    export_job_file(args)
    if getattr(args, "run", None):
        logging.info("Run Airflow Scheduler")
        with Mute():
            add_run_info(args)
            scheduler(args)
        print(get_workflow_output(args.dag_id))


def main(argsl=None):
    if argsl is None:
        argsl = sys.argv[1:]
    argsl.append("")  # To avoid raising error when argsl is empty
    args, _ = arg_parser().parse_known_args(argsl)
    args = normalize_args(args, skip_list=["func", "uid", "limit", "dag_timeout", "threads",
                                           "web_interval", "web_workers", "run", "auto", "manual", "list", "quiet"])
    with Mute():
        reset_root_logger(args.quiet)
    args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
