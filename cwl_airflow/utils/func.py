import os
import tempfile
from datetime import datetime
from cwl_airflow.utils.utils import (set_logger,
                                     gen_dag_id,
                                     get_folder,
                                     load_job,
                                     list_files)
from cwl_airflow.dag_components.cwldag import CWLDAG
from cwl_airflow.dag_components.jobdispatcher import JobDispatcher
from cwl_airflow.dag_components.jobcleanup import JobCleanup


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
        'start_date': job["creation_date"],
        'output_folder': get_folder(job["content"]["output_folder"]),
        'tmp_folder':    get_folder(job["content"].get("tmp_folder", tempfile.mkdtemp())),
        'basedir': os.path.abspath(os.path.dirname(job["path"])),  # Get rid of it, or move to the place where it should be
        "cwl_workflow": job["content"]["workflow"]
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
