#!/usr/bin/env python
import sys

from airflow.configuration import conf
from datetime import datetime
from cwl_airflow.modules.cwldag import CWLDAG
from cwl_airflow.modules.jobdispatcher import JobDispatcher
from cwl_airflow.modules.jobcleanup import JobCleanup
import cwltool.errors
import os
import shutil
import ruamel.yaml as yaml
import logging
import tempfile
import re
from cwl_airflow.modules.cwlutils import conf_get_default, get_only_files

class SkipException(Exception):
    pass

def get_max_jobs_to_run():
    try:
        max_jobs_to_run = int(conf_get_default('cwl', 'MAX_JOBS_TO_RUN', 1))
    except ValueError:
        logging.error('Error evaluating MAX_JOBS_TO_RUN as integer: {0}'.format (conf_get_default('cwl', 'MAX_JOBS_TO_RUN', 1)))
        sys.exit()
    return max_jobs_to_run

def eval_log_level(key):
    log_depth = {
        'CRITICAL': 50,
        'ERROR': 40,
        'WARNING': 30,
        'INFO': 20,
        'DEBUG': 10,
        'NOTSET': 0
    }
    return log_depth[key] if key in log_depth else 20

def fail_callback(context):
    job_file = context["dag"].default_args["job_filename"]
    shutil.move(job_file, os.path.join('/'.join(job_file.split('/')[0:-2]), 'fail'))

def gen_uid (job_file):
    with open(job_file, 'r') as f:
        job = yaml.safe_load(f)
    return job.get("uid", '.'.join(job_file.split("/")[-1].split('.')[0:-1]))


def gen_dag_id (workflow_file, job_file):
    return ".".join(workflow_file.split("/")[-1].split(".")[0:-1]) + "-" + gen_uid(
        job_file) + "-" + datetime.fromtimestamp(os.path.getctime(job_file)).isoformat().replace(':', '-')


def make_dag(job_file, workflow_file):
    try:
        with open(job_file, 'r') as f:
            job = yaml.safe_load(f)
    except IOError as ex:
        raise SkipException ("Job file of finished workflow was deleted by its jobcleanup task: "+str(ex))

    dag_id = gen_dag_id(workflow_file, job_file)

    start_day = datetime.fromtimestamp(os.path.getctime(job_file))

    basedir = os.path.abspath(os.path.dirname(job_file))

    output_folder = job.get('output_folder', os.path.join(conf_get_default('cwl', 'OUTPUT_FOLDER', os.getcwd()), dag_id))
    output_folder = output_folder if os.path.isabs(output_folder) else os.path.normpath(os.path.join(basedir, output_folder))

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        os.chmod(output_folder, 0775)

    tmp_folder = job.get('tmp_folder', conf_get_default('cwl', 'TMP_FOLDER', tempfile.mkdtemp()))
    tmp_folder = tmp_folder if os.path.isabs(tmp_folder) else os.path.normpath(os.path.join(basedir, tmp_folder))

    if not os.path.exists(tmp_folder):
        os.makedirs(tmp_folder)
        os.chmod(tmp_folder, 0755)

    owner = job.get('author', 'CWL-Airflow')

    default_args = {
        'owner': owner,
        'start_date': start_day,
        'email_on_failure': False,
        'email_on_retry': False,
        'end_date': None, # Open ended schedule
        'on_failure_callback': fail_callback,
        'output_folder': output_folder,
        'tmp_folder': tmp_folder,

        'print_deps': False,
        'print_pre': False,
        'print_rdf': False,
        'print_dot': False,
        'relative_deps': False,
        'use_container': True,
        'preserve_environment': ["PATH"],
        'preserve_entire_environment': False,
        "rm_container": True,
        'print_input_deps': False,
        'cachedir': None,
        'rm_tmpdir': True,
        'move_outputs': 'move',
        'enable_pull': True,
        'eval_timeout': 20,
        'quiet': False,
        # # 'debug': False,   # TODO Check if it influence somehow. It shouldn't
        'version': False,
        'enable_dev': False,
        'enable_ext': False,
        'strict': conf_get_default('cwl', 'STRICT', 'False').lower() in ['true', '1', 't', 'y', 'yes'],
        'rdf_serializer': None,
        'basedir': basedir,
        'tool_help': False,
        # 'workflow': None,
        # 'job_order': None,
        "job_filename": job_file,
        'pack': False,
        'on_error': 'continue',
        'relax_path_checks': False,
        'validate': False,
        'compute_checksum': True,
        "no_match_user" : False,
        "cwl_workflow" : workflow_file
    }

    dag = CWLDAG(
        dag_id=dag_id,
        schedule_interval = '@once',
        default_args=default_args)
    dag.create()
    dag.assign_job_dispatcher(JobDispatcher(task_id="read", read_file=job_file, dag=dag))
    dag.assign_job_cleanup(JobCleanup(task_id="cleanup",
                                      outputs=dag.get_output_list(),
                                      rm_files=[job_file],
                                      rm_files_dest_folder=os.path.join('/'.join(job_file.split('/')[0:-2]), 'success'),
                                      dag=dag))
    globals()[dag_id] = dag


def find_workflow(job_filename):
    workflows_folder = conf.get('cwl', 'CWL_WORKFLOWS')
    all_workflows = {}
    for root, dirs, files in os.walk(workflows_folder):
        all_workflows.update( \
                              { filename: os.path.join(root, filename) \
                                for filename in files \
                                if  os.path.splitext(filename)[1]=='.cwl' \
                                    and (filename not in all_workflows \
                                                 or os.path.getctime(os.path.join(root, filename)) < \
                                                 os.path.getctime( all_workflows[filename]) ) \
                              } \
                            )
    for key in sorted(all_workflows, key=len, reverse=True):
        if re.match(os.path.splitext(key)[0], os.path.basename(job_filename)):
            return all_workflows[key]
    raise cwltool.errors.WorkflowException("Correspondent workflow is not found")


def get_jobs_folder_structure(monitor_folder):
    jobs = []
    for root, dirs, files in os.walk(monitor_folder):
        if 'new' in dirs:
            job_rec = { "new": os.path.join(root, "new"),
                        "running": os.path.join(root, "running"),
                        "fail": os.path.join(root, "fail"),
                        "success": os.path.join(root, "success")}
            for key,value in job_rec.iteritems():
                if not os.path.exists(value):
                    raise ValueError("Failed to find {}".format(value))
            jobs.append(job_rec)
    return jobs


logging.getLogger('cwltool').setLevel(eval_log_level(conf_get_default('cwl', 'LOG_LEVEL', 'INFO').upper()))
logging.getLogger('salad').setLevel(eval_log_level(conf_get_default('cwl', 'LOG_LEVEL', 'INFO').upper()))

max_jobs_to_run = get_max_jobs_to_run()
monitor_folder = conf.get('cwl', 'CWL_JOBS')

jobs_list = get_jobs_folder_structure (monitor_folder)

tot_files_run = len(get_only_files(jobs_list, key="running"))
tot_files_new = len(get_only_files(jobs_list, key="new"))

# add new jobs into running
if tot_files_run < max_jobs_to_run and tot_files_new > 0:
    for i in range(min(max_jobs_to_run - tot_files_run, tot_files_new)):
        oldest = min(get_only_files(jobs_list, key="new", excl_key='running'), key=os.path.getctime)
        print "mv {0} {1}".format (oldest, os.path.join('/'.join(oldest.split('/')[0:-2]), 'running'))
        try:
            shutil.move(oldest, os.path.join('/'.join(oldest.split('/')[0:-2]), 'running'))
        except IOError as ex:
            print "Job file was moved to running folder by another dag: "+str(ex)



for fn in get_only_files(jobs_list, key="running"):
    try:
        make_dag(fn, find_workflow(fn))
    except SkipException as ex:
        print "SKIP exception: ", str(ex)
        pass
    except Exception as ex:
        print "FAIL exception: ", str(ex)
        # shutil.move(fn, os.path.join('/'.join(fn.split('/')[0:-2]), 'fail'))

