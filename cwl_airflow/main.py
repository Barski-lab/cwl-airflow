#!/usr/bin/env python
import argparse
from typing import Text
import os
import ruamel.yaml as yaml
from argparse import Namespace
import logging
import shutil
import sys
import tempfile
from datetime import datetime
import cwltool.errors
import errno


def suppress_stdout():
    global null_fds
    null_fds = [os.open(os.devnull, os.O_RDWR) for x in xrange(2)]
    global backup_fds
    backup_fds = os.dup(1), os.dup(2)
    os.dup2(null_fds[0], 1)
    os.dup2(null_fds[1], 2)


def restore_stdout():
    os.dup2(backup_fds[0], 1)
    os.dup2(backup_fds[1], 2)
    os.close(null_fds[0])
    os.close(null_fds[1])


suppress_stdout()
from airflow.bin.cli import backfill
from airflow import models, settings
from airflow import configuration
from cwl_airflow.modules.cwldag import CWLDAG
from cwl_airflow.modules.jobdispatcher import JobDispatcher
from cwl_airflow.modules.jobcleanup import JobCleanup
from cwl_airflow.modules.cwlutils import (conf_get_default, set_permissions)

restore_stdout()


def arg_parser():
    """Returns argument parser"""

    # PARENT PARSER
    parent_parser = argparse.ArgumentParser(add_help=False)

    # GENERAL PARSER
    general_parser = argparse.ArgumentParser(description='cwl-airflow')
    subparsers = general_parser.add_subparsers()
    subparsers.required = True
    init_parser = subparsers.add_parser('init', help="Init cwl-airflow", parents=[parent_parser])
    run_parser = subparsers.add_parser('run',  help="Run workflow", parents=[parent_parser])

    # INIT PARSER
    init_parser.set_defaults(func=run_init)

    # RUN PARSER
    #    from airflow
    run_parser.add_argument ("-t", "--task_regex", help="The regex to filter specific task_ids to backfill (optional)")
    run_parser.add_argument("-m", "--mark_success", help="Mark jobs as succeeded without running them", action="store_true")
    run_parser.add_argument("-l", "--local", help="Run the task using the LocalExecutor", action="store_true")
    run_parser.add_argument("-x", "--donot_pickle",
                            help="Do not attempt to pickle the DAG object to send over to the workers, just tell the workers to run their version of the code.",
                            action="store_true")
    run_parser.add_argument("-a", "--include_adhoc", help="Include dags with the adhoc parameter.", action="store_true")
    run_parser.add_argument("-i", "--ignore_dependencies", help="Skip upstream tasks, run only the tasks matching the regexp. Only works in conjunction with task_regex", action="store_true")
    run_parser.add_argument("-I", "--ignore_first_depends_on_past", help="Ignores depends_on_past dependencies for the first set of tasks only (subsequent executions in the backfill DO respect depends_on_past).", action="store_true")
    run_parser.add_argument("--pool", help="Resource pool to use")
    run_parser.add_argument("-dr", "--dry_run", help="Perform a dry run", action="store_true")
    #    from cwltool
    run_parser.add_argument("--outdir", help="Output folder to save results")
    run_parser.add_argument("--tmp-folder", help="Temp folder to store data between execution of airflow tasks/steps")
    run_parser.add_argument("--tmpdir-prefix", help="Path prefix for temporary directories")
    run_parser.add_argument("--tmp-outdir-prefix", help="Path prefix for intermediate output directories")
    run_parser.add_argument("--quiet", action="store_true", help="Print only workflow execultion results")
    run_parser.add_argument("workflow", type=Text)
    run_parser.add_argument("job", type=Text)
    #    additional
    run_parser.add_argument("--ignore-def-outdir", action="store_true", help="Disable default output directory to be set to current directory. Use OUTPUT_FOLDER from Airflow configuration file instead")
    run_parser.set_defaults(func=run_job)

    return general_parser


def create_backup(args):
    del args['func']  # When creating backup we don't need func to be included
    with open(os.path.join(os.getcwd(), "run_param.tmp"), 'w') as backup_file:
        yaml.safe_dump(args, stream=backup_file)

def remove_backup():
    os.remove(os.path.join(os.getcwd(), "run_param.tmp"))

def read_backup():
    with open(os.path.join(os.getcwd(), "run_param.tmp"), 'r') as backup_file:
        return yaml.safe_load(backup_file)

def gen_uid (job_file):
    with open(job_file, 'r') as f:
        job = yaml.safe_load(f)
    return job.get("uid", '.'.join(job_file.split("/")[-1].split('.')[0:-1]))


def gen_dag_id (workflow_file, job_file):
    dag_id = ".".join(workflow_file.split("/")[-1].split(".")[0:-1]) + "-" + gen_uid(job_file) + "-" + datetime.fromtimestamp(os.path.getctime(job_file)).isoformat().replace(':', '-')
    duplicate_dag_id = [dag_run.dag_id for dag_run in settings.Session().query(models.DagRun).filter(models.DagRun.dag_id.like(dag_id+'%'))]
    if dag_id not in duplicate_dag_id:
        return dag_id
    else:
        sufix = 1
        while dag_id+'_'+str(sufix) in duplicate_dag_id:
            sufix = sufix+1
        return dag_id+'_'+str(sufix)


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


def set_logger ():
    cwl_logger = logging.getLogger("cwltool")
    cwl_logger.addHandler(logging.StreamHandler())
    cwl_logger.setLevel(eval_log_level(conf_get_default('cwl','LOG_LEVEL','INFO').upper()))


def get_log_filename (args):
    log_base = os.path.expanduser(configuration.get('core', 'BASE_LOG_FOLDER'))
    directory = log_base + "/{args.dag_id}/cleanup".format(args=args)
    return "{0}/{1}".format(directory, args.start_date.isoformat())


def clear_previous_log (args):
    log_base = os.path.expanduser(configuration.get('core', 'BASE_LOG_FOLDER'))
    directory = log_base + "/{args.dag_id}".format(args=args)
    shutil.rmtree(directory, True)


def print_workflow_output (args):
    found_output = False
    results = ''
    with open(get_log_filename(args), 'r') as results_file:
        for line in results_file.readlines():
            if 'Subtask:' not in line: continue
            if 'WORKFLOW RESULTS' in line:
                found_output = True
                results = ''
                continue
            if found_output:
                results = results + line.split('Subtask: ')[1]
    print results.rstrip('\n')


def update_config(configuration):
    configuration.set('core', 'dags_are_paused_at_creation', 'False')
    configuration.set('core', 'load_examples', 'False')
    # set default [cwl] section if it doesn't exist
    if not configuration.conf.has_section('cwl'):
        configuration.conf.add_section('cwl')
        configuration.set('cwl', 'cwl_workflows',    os.path.abspath(os.path.join(configuration.get('core','airflow_home'), 'cwl', 'workflows')))
        configuration.set('cwl', 'cwl_jobs',         os.path.abspath(os.path.join(configuration.get('core','airflow_home'), 'cwl', 'jobs')))
        configuration.set('cwl', 'output_folder',    os.path.abspath(os.path.join(configuration.get('core','airflow_home'), 'cwl', 'output')))
        configuration.set('cwl', 'tmp_folder',       os.path.abspath(os.path.join(configuration.get('core','airflow_home'), 'cwl', 'tmp')))
        configuration.set('cwl', 'max_jobs_to_run', '2')
        configuration.set('cwl', 'log_level',       'ERROR')
        configuration.set('cwl', 'strict',          'False')


def copy_cwl_dag(configuration):
    current_folder = os.path.dirname (__file__)
    cwl_dag_folder = os.path.join(configuration.get('core', 'dags_folder'), os.path.basename(current_folder))  # dags_folder/cwl_airflow
    if os.path.exists(cwl_dag_folder):
        shutil.rmtree(cwl_dag_folder)
    shutil.copytree(current_folder, cwl_dag_folder, ignore=shutil.ignore_patterns('*.pyc', 'main.py', 'git_version'))
    set_permissions(cwl_dag_folder, dir_perm=0775, file_perm=0664)


def create_folders(configuration):
    '''
    Creates all required for cwl folders.
    If there is a problem not related to already existing folder - raise exception
    :param configuration: airflow configuration ConfigParser
    :return: None
    '''
    folder_list = []
    folder_list.append(configuration.get('cwl', 'cwl_workflows'))
    folder_list.append(configuration.get('cwl', 'output_folder'))
    folder_list.append(configuration.get('cwl', 'tmp_folder'))
    folder_list.append(os.path.join(configuration.get('cwl', 'cwl_jobs'), 'new'))
    folder_list.append(os.path.join(configuration.get('cwl', 'cwl_jobs'), 'running'))
    folder_list.append(os.path.join(configuration.get('cwl', 'cwl_jobs'), 'success'))
    folder_list.append(os.path.join(configuration.get('cwl', 'cwl_jobs'), 'fail'))
    for folder in folder_list:
        try:
            os.makedirs(folder)
            set_permissions(folder, dir_perm=0775, file_perm=0664)
        except OSError as ex:
            if ex.errno != errno.EEXIST:
                raise  # raises the error again if it wasn't a problem of already existed folder


def run_init (**kwargs):
    airflow_cfg = os.path.join(os.path.expanduser(os.environ.get('AIRFLOW_HOME', '~/airflow')), 'airflow.cfg')
    update_config(configuration)
    copy_cwl_dag (configuration)   # raise if not enough permissions to write file
    create_folders(configuration)  # raise if not enough permissions to create a folder
    with open(airflow_cfg, 'w') as airflow_cfg_file:  # Writing changes to airflow.cfg
        configuration.conf.write(airflow_cfg_file)


def run_job (**kwargs):
    kwargs['dag_id'] = gen_dag_id(kwargs.get('workflow'), kwargs.get('job'))
    kwargs['subdir'] = os.path.splitext(__file__)[0]+'.py'
    kwargs['start_date'] = datetime.fromtimestamp(os.path.getctime(kwargs.get('job')))
    kwargs['end_date'] = datetime.fromtimestamp(os.path.getctime(kwargs.get('job')))
    create_backup(kwargs)
    try:
        args = Namespace (**kwargs)
        # clear_previous_log(args)
        if args.quiet:
            suppress_stdout()
        backfill (args)
        if args.quiet:
            restore_stdout()
        print_workflow_output (args)
        remove_backup()
    except KeyboardInterrupt:
        remove_backup()
    except Exception:
        remove_backup()
        raise


def main(argsl=None):
    if argsl is None:
        argsl = sys.argv[1:]
    args, _ = arg_parser().parse_known_args(argsl)
    args.func(**args.__dict__)


def get_tmp_folder (args, job_entry, job):
    if not args.get('tmp_folder'):
        tmp_folder = job_entry.get('tmp_folder', conf_get_default('cwl', 'TMP_FOLDER', tempfile.mkdtemp()))
        return tmp_folder if os.path.isabs(tmp_folder) else os.path.normpath(os.path.join(os.path.dirname(job), tmp_folder))
    else:
        return os.path.abspath(args.get('tmp_folder'))


def get_output_folder (args, job_entry, job, workflow_file):
    if not args.get('outdir'):
        if args.get('ignore_def_outdir'):
            default_outdir = os.path.join(conf_get_default('cwl', 'OUTPUT_FOLDER', os.getcwd()), gen_dag_id(workflow_file,job))
        else:
            default_outdir = os.path.abspath(os.getcwd())
        output_folder = job_entry.get('output_folder', default_outdir)
        return output_folder if os.path.isabs(output_folder) else os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(job)), output_folder))
    else:
        return os.path.abspath(args.get('outdir'))


def make_dag(args):
    set_logger()
    job = os.path.abspath(args['job'])
    workflow = os.path.abspath(args['workflow'])

    with open(job, 'r') as f:
        job_entry = yaml.safe_load(f)

    basedir = os.path.dirname(job)
    output_folder = get_output_folder(args, job_entry, job, workflow)
    tmp_folder = get_tmp_folder (args, job_entry, job)

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        os.chmod(output_folder, 0775)

    if not os.path.exists(tmp_folder):
        os.makedirs(tmp_folder)
        os.chmod(tmp_folder, 0755)

    owner = job_entry.get('author', 'CWL-Airflow')

    default_args = {
        'owner': owner,
        'start_date': args['start_date'],
        'email_on_failure': False,
        'email_on_retry': False,
        'end_date': None, # Open ended schedule
        'output_folder': output_folder,
        'tmp_folder': tmp_folder,

        'print_deps': False,
        'print_pre': False,
        'print_rdf': False,
        'print_dot': False,
        'relative_deps': False,
        'tmp_outdir_prefix': os.path.abspath(args.get('tmp_outdir_prefix')) if args.get('tmp_outdir_prefix') else None,
        'use_container': True,
        'preserve_environment': ["PATH"],
        'preserve_entire_environment': False,
        "rm_container": True,
        'tmpdir_prefix': os.path.abspath(args.get('tmpdir_prefix')) if args.get('tmpdir_prefix') else None,
        'print_input_deps': False,
        'cachedir': None,
        'rm_tmpdir': True,
        'move_outputs': 'move',
        'enable_pull': True,
        'eval_timeout': 20,
        'quiet': False,
        'version': False,
        'enable_dev': False,
        'enable_ext': False,
        'strict': conf_get_default('cwl', 'STRICT', 'False').lower() in ['true', '1', 't', 'y', 'yes'],
        'rdf_serializer': None,
        'basedir': basedir,
        'tool_help': False,
        'pack': False,
        'on_error': 'continue',
        'relax_path_checks': False,
        'validate': False,
        'compute_checksum': True,
        "no_match_user" : False,
        "cwl_workflow" : workflow
    }

    dag = CWLDAG(
        dag_id=args["dag_id"],
        schedule_interval = '@once',
        default_args=default_args)
    dag.create()
    dag.assign_job_dispatcher(JobDispatcher(task_id="read", read_file=job, dag=dag))
    dag.assign_job_cleanup(JobCleanup(task_id="cleanup", outputs=dag.get_output_list(), dag=dag))
    globals()[args["dag_id"]] = dag

try:
    make_dag(read_backup())
except cwltool.errors.UnsupportedRequirement as feature_ex:
    print feature_ex
    remove_backup()
    sys.exit(33)
except Exception as ex:
    pass

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
