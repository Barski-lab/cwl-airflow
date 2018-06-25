import os
import tempfile
import ruamel.yaml as yaml
from json import dumps
from datetime import datetime
from airflow import configuration
from airflow.bin.cli import get_dag, CLIFactory
from cwl_airflow.utils.utils import (set_logger,
                                     gen_dag_id,
                                     get_folder,
                                     load_job,
                                     list_files,
                                     export_to_file)
from cwl_airflow.dag_components.cwldag import CWLDAG
from cwl_airflow.dag_components.jobdispatcher import JobDispatcher
from cwl_airflow.dag_components.jobcleanup import JobCleanup


def export_job_file(args):
    with open(args.job, 'r') as input_stream:
        job_entry = yaml.safe_load(input_stream)
        job_entry['workflow'] = args.workflow
        job_entry['output_folder'] = args.output_folder
        if args.tmp_folder:
            job_entry['tmp_folder'] = args.tmp_folder
        export_to_file(os.path.join(configuration.get('biowardrobe', 'jobs'), os.path.basename(args.job)),
                       dumps(job_entry, indent=4))


def update_args(args):
    vars(args).update({arg_name: arg_value.default for arg_name, arg_value in CLIFactory.args.items()
                       if arg_name in CLIFactory.subparsers_dict['scheduler']['args']})
    args.dag_id = gen_dag_id(args.workflow, os.path.join(configuration.get('biowardrobe', 'jobs'), os.path.basename(args.job)))
    args.num_runs = len(get_dag(args).tasks) + 3


def get_active_jobs(jobs_folder, limit=10):
    """
    :param jobs_folder: job_folder: abs path to the folder with job json files  
    :param limit: max number of jobs to return
    :return: 
    """
    all_jobs = []
    for job_path in list_files(abs_path=jobs_folder, ext=[".json", ".yml", ".yaml"]):
        job_content = load_job(job_path)
        all_jobs.append({"content": job_content,
                         "path": job_path,
                         "creation_date": datetime.fromtimestamp(os.path.getctime(job_path)),
                         "dag_id": gen_dag_id(job_content["workflow"], job_path)})
    all_jobs = sorted(all_jobs, key=lambda k: k["creation_date"], reverse=True)
    return all_jobs[:limit]


def make_dag(job):
    """
    :param job: {"content": job_entry,
                 "path": job,
                 "creation_date": datetime.fromtimestamp(os.path.getctime(job_path)),
                 "dag_id": gen_dag_id(job_entry["workflow"], job_path)}
    :return:
    """
    set_logger()
    default_args = {
        'owner': job["content"].get("author", "cwl-airflow"),
        'start_date':    job["creation_date"],
        'output_folder': get_folder(job["content"]["output_folder"]),
        'tmp_folder':    tempfile.mkdtemp(dir=job["content"].get("tmp_folder", None), prefix="dag_tmp_"),
        'basedir':       os.path.abspath(os.path.dirname(job["path"])),
        "main_workflow": job["content"]["workflow"]
    }

    dag = CWLDAG(
        dag_id=job["dag_id"],
        schedule_interval='@once',
        default_args=default_args)
    dag.create()
    dag.assign_job_dispatcher(JobDispatcher(task_id="read", read_file=job["path"], dag=dag))
    dag.assign_job_cleanup(JobCleanup(task_id="cleanup",
                                      outputs=dag.get_output_list(),
                                      dag=dag))
    return dag
