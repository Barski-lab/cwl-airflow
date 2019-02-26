import os
import sys
from six.moves import configparser
import argparse
import uuid
import logging
import shutil
import subprocess
from multiprocessing import Process
from json import dumps
from datetime import datetime
from cwl_airflow.utils.mute import Mute
from airflow import conf as conf
from airflow.models import DagRun, DagPickle, TaskInstance, TaskFail, Log, DagModel, XCom, DagStat, SlaMiss
from airflow.utils.db import provide_session
from airflow.utils.state import State
from airflow.settings import DAGS_FOLDER, AIRFLOW_HOME
from airflow.bin.cli import get_dag, CLIFactory, scheduler
from airflow.exceptions import AirflowConfigException
from cwl_airflow.utils.utils import (set_logger,
                                     gen_dag_id,
                                     get_folder,
                                     load_job,
                                     list_files,
                                     export_to_file,
                                     norm_path,
                                     get_files,
                                     conf_get_default)
from cwl_airflow.dag_components.cwldag import CWLDAG
from cwl_airflow.dag_components.jobdispatcher import JobDispatcher
from cwl_airflow.dag_components.jobcleanup import JobCleanup


def get_demo_workflow(target_wf=None, job_ext=".json"):
    workflows = get_files(os.path.join(AIRFLOW_HOME, "demo/cwl/workflows"))
    jobs = get_files(os.path.join(AIRFLOW_HOME, "demo/job"))
    combined_data = []
    for wf_name, wf_path in workflows.items():
        job_name = os.path.splitext(wf_name)[0] + job_ext
        if job_name in jobs:
            combined_data.append({"workflow": {"name": wf_name,
                                               "path": wf_path},
                                  "job": {"name": job_name,
                                          "path": jobs[job_name]}
                                  })
    return [item for item in combined_data if item["workflow"]["name"] == os.path.basename(target_wf)] if target_wf else combined_data


def export_job_file(args):
    try:
        job_entry = load_job(args.job)
        del job_entry["id"]
    except Exception:
        job_entry = {}
        args.job = "empty.json"
    job_entry['workflow'] = job_entry.get("workflow", args.workflow)
    job_entry['output_folder'] = job_entry.get("output_folder", args.output_folder)
    job_entry["uid"] = job_entry.get("uid", args.uid)
    tmp_folder = job_entry.get("tmp_folder", args.tmp_folder)
    if tmp_folder:
        job_entry['tmp_folder'] = tmp_folder
    root, ext = os.path.splitext(os.path.basename(args.job))
    copy_counter = 0
    while True:
        suffix = "" if copy_counter == 0 else "-" + str(copy_counter)
        output_filename = os.path.join(conf.get('cwl', 'jobs'), root + suffix + ext)
        if not os.path.exists(output_filename):
            args.job = output_filename
            export_to_file(args.job, dumps(job_entry, indent=4))
            logging.info("Save job file as\n- {}".format(args.job))
            break
        else:
            copy_counter += 1


def add_run_info(args):
    vars(args).update(vars(get_airflow_default_args("scheduler")))
    args.dag_id = gen_dag_id(os.path.join(conf.get('cwl', 'jobs'), os.path.basename(args.job)))
    args.num_runs = len(get_dag(args).tasks) + 3


def get_updated_args(args, workflow, keep_uid=False, keep_output_folder=False):
    updated_args = argparse.Namespace(**vars(args))
    updated_args.workflow = workflow["workflow"]["path"]
    updated_args.job = workflow["job"]["path"]
    if not keep_uid:
        updated_args.uid = str(uuid.uuid4())
    if not keep_output_folder:
        updated_args.output_folder = get_folder(os.path.join(args.output_folder, updated_args.uid))
    return updated_args


def get_active_jobs(jobs_folder, limit=10):
    """
    :param jobs_folder: job_folder: abs path to the folder with job json files  
    :param limit: max number of jobs to return
    :return: 
    """
    all_jobs = []
    for job_path in list_files(abs_path=jobs_folder, ext=[".json", ".yml", ".yaml"]):
        dag_id = gen_dag_id(job_path)
        dag_runs = DagRun.find(dag_id)
        all_jobs.append({"path": job_path,
                         "creation_date": datetime.utcfromtimestamp(os.path.getctime(job_path)),
                         "content": load_job(job_path),
                         "dag_id": dag_id,
                         "state": dag_runs[0].state if len(dag_runs) > 0 else State.NONE})
    success_jobs = sorted([j for j in all_jobs if j["state"] == State.SUCCESS], key=lambda k: k["creation_date"], reverse=True)[:limit]
    running_jobs = sorted([j for j in all_jobs if j["state"] == State.RUNNING], key=lambda k: k["creation_date"], reverse=True)[:limit]
    failed_jobs =  sorted([j for j in all_jobs if j["state"] == State.FAILED],  key=lambda k: k["creation_date"], reverse=True)[:limit]
    unknown_jobs = sorted([j for j in all_jobs if j["state"] == State.NONE],    key=lambda k: k["creation_date"], reverse=True)[:limit]
    return success_jobs + running_jobs + failed_jobs + unknown_jobs


def make_dag(job):
    """
    :param job: {"content": job_entry,
                 "path": job,
                 "creation_date": datetime.utcfromtimestamp(os.path.getctime(job_path)),
                 "dag_id": gen_dag_id(job_entry["workflow"], job_path)}
    :return:
    """
    set_logger()
    default_args = {
        'start_date': job["creation_date"],
        "job_data":   job
    }

    dag = CWLDAG(
        dag_id=job["dag_id"],
        schedule_interval='@once',
        default_args=default_args)
    dag.create()
    dag.assign_job_dispatcher(JobDispatcher(dag=dag))
    dag.assign_job_cleanup(JobCleanup(dag=dag))
    return dag


def update_config(args):
    logging.info("Update Airflow configuration")
    with open(conf.AIRFLOW_CONFIG, 'w') as output_stream:
        try:
            conf.conf.add_section('cwl')
        except configparser.DuplicateSectionError:
            pass
        conf.set('core', 'dags_are_paused_at_creation', 'False')
        conf.set('core', 'load_examples', 'False')
        conf.set('cwl', 'jobs', str(args.jobs))
        conf.set('cwl', 'limit', str(args.limit))
        conf.set('cwl', 'logging_level', conf_get_default('cwl', 'logging_level', 'ERROR'))  # To supress all useless output from cwltool's functions
        conf.set('core', 'dagbag_import_timeout', str(args.dag_timeout))
        conf.set('scheduler', 'max_threads', str(args.threads))
        conf.set('webserver', 'worker_refresh_interval', str(args.web_interval))
        conf.set('webserver', 'worker_refresh_batch_size', str(args.web_workers))
        conf.set('webserver', 'hide_paused_dags_by_default', 'True')
        conf.conf.write(output_stream)


def export_dags():
    logging.info("Export cwl_dag.py to\n- {}".format(DAGS_FOLDER))
    dag_content = u"#!/usr/bin/env python3\nfrom airflow import DAG\nfrom cwl_airflow.create_dag import create_dags\nfor id, dag in create_dags().items():\n    globals()[id] = dag"
    export_to_file(os.path.join(DAGS_FOLDER, "cwl_dag.py"), dag_content)


def create_folders():
    logging.info("Create folders for jobs and dags\n- {}\n- {}".format(conf.get('cwl', 'jobs'), DAGS_FOLDER))
    get_folder(conf.get('cwl', 'jobs'))
    get_folder(DAGS_FOLDER)


def get_airflow_default_args(subparser):
    args, _ = CLIFactory.get_parser().parse_known_args([subparser])
    delattr(args, 'func')
    return args


def start_background_scheduler():
    logging.info("Starting Airflow Scheduler in background")
    scheduler_thread = Process(target=scheduler, args=(get_airflow_default_args("scheduler"),))
    with Mute():
        scheduler_thread.start()


@provide_session
def remove_dag(dag_id, session=None):
    """
    Clean the following tables
    DagPickle    # dag_pickle              connected to DagModel by pickle_id
    TaskInstance # task_instance           by dag_id
    TaskFail     # task_fail               by dag_id
    Log          # log                     by dag_id
    DagModel     # dag                     by dag_id
    XCom         # xcom                    by dag_id
    DagStat      # dag_stats               by dag_id
    DagRun       # dag_run                 by dag_id
    SlaMiss      # sla_miss                by dag_id
    :param dag_id: DAG id to delete
    :param session: is provided by @provide_session
    :return: None
    """
    logging.info("Remove dag\n- {}".format(dag_id))
    dag = session.query(DagModel).filter(DagModel.dag_id == dag_id).first()
    if dag and dag.pickle_id:
        session.query(DagPickle).filter(DagPickle.id == dag.pickle_id).delete()
        session.commit()
    models = [TaskInstance, TaskFail, Log, DagModel, XCom, DagStat, DagRun, SlaMiss]
    for model in models:
        session.query(model).filter(model.dag_id == dag_id).delete()
        session.commit()


def clean_jobs(folder=None):
    folder = folder if folder else conf_get_default('cwl', 'jobs', None)
    if folder and os.path.isdir(folder):
        logging.info("Cleaning jobs folder\n- {}".format(folder))
        for item in os.listdir(folder):
            path = os.path.join(folder, item)
            dag_id = gen_dag_id(path)
            try:
                os.remove(path)
                logging.info("Remove job file\n- {}".format(path))
                remove_dag(dag_id)
            except OSError:
                shutil.rmtree(path, ignore_errors=False)


def asset_conf(mode=None):

    def config():
        conf.get('cwl', 'jobs')
        conf.get('cwl', 'limit')

    def paths(items=[]):
        for item in items:
            if not os.path.exists(item):
                raise OSError(item)

    def docker():
        with open(os.devnull, 'w') as devnull:
            subprocess.check_call("docker -v", shell=True, stdout=devnull)

    def docker_demo_mount():
        with open(os.devnull, 'w') as devnull:
            subprocess.check_call("docker run --rm -v {}:/tmp hello-world".format(AIRFLOW_HOME), shell=True, stdout=devnull)

    def docker_pull():
        with open(os.devnull, 'w') as devnull:
            subprocess.check_call("docker pull hello-world", shell=True, stdout=devnull)

    def airflow():
        with open(os.devnull, 'w') as devnull:
            subprocess.check_call("airflow -h", shell=True, stdout=devnull)

    def demo_paths():
        paths([os.path.join(AIRFLOW_HOME, "demo", name) for name in ["cwl", "data", "job"]])

    def general_paths():
        paths([conf.get('cwl', 'jobs'), DAGS_FOLDER, os.path.join(DAGS_FOLDER, "cwl_dag.py")])

    check_set = {
        "init": [airflow, docker],
        "demo": [airflow, docker, docker_pull, docker_demo_mount, general_paths, demo_paths, config],
        None:   [airflow, docker, general_paths, config]
    }

    for check_criteria in check_set[mode]:
        try:
            check_criteria()
        except AirflowConfigException as ex:
            logging.error("Missing required configuration\n- {}\n- run cwl-airflow init".format(str(ex)))
            sys.exit(0)
        except OSError as ex:
            logging.error("Missing required file or directory\n- {}\n- run cwl-airflow init".format(str(ex)))
            sys.exit(0)
        except subprocess.CalledProcessError as ex:
            logging.error("Missing or not configured required tool\n- {}".format(str(ex)))
            sys.exit(0)
        except Exception as ex:
            logging.error("Unexpected exception\n- {}".format(str(ex)))
            sys.exit(1)


def get_webserver_url():
    return "{}:{}".format(conf.get('webserver', 'WEB_SERVER_HOST'), conf.get('webserver', 'WEB_SERVER_PORT'))


def copy_demo_workflows():
    src = norm_path(os.path.join(os.path.dirname(os.path.abspath(os.path.join(__file__, "../"))), "tests"))
    dst = os.path.join(AIRFLOW_HOME, "demo")
    logging.info("Copy demo workflows\n- from: {}\n- to: {}".format(src, dst))
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
