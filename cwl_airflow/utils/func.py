import os
import ruamel.yaml as yaml
from datetime import datetime
from cwl_airflow.utils.utils import (set_logger,
                                     find_workflow,
                                     gen_dag_id,
                                     create_output_folder,
                                     create_tmp_folder,
                                     conf_get_default)
from cwl_airflow.dag_components.cwldag import CWLDAG
from cwl_airflow.dag_components.jobdispatcher import JobDispatcher
from cwl_airflow.dag_components.jobcleanup import JobCleanup


def make_dag(args):
    set_logger()
    job = os.path.abspath(args['job'])
    basedir = os.path.dirname(job)
    with open(job, 'r') as input_stream:
        job_entry = yaml.safe_load(input_stream)
    workflow = job_entry.get('workflow', find_workflow(job))
    dag_id = gen_dag_id(workflow, job)

    default_args = {
        'owner': job_entry.get('author', 'CWL-Airflow'),
        'start_date': datetime.fromtimestamp(os.path.getctime(job)),
        'output_folder': create_output_folder(args, job_entry, job, workflow),
        'tmp_folder': create_tmp_folder(args, job_entry, job),
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
        "no_match_user": False,
        "cwl_workflow": workflow
    }

    dag = CWLDAG(
        dag_id=dag_id,
        schedule_interval = '@once',
        default_args=default_args)
    dag.create()
    dag.assign_job_dispatcher(JobDispatcher(task_id="read", read_file=job, dag=dag))
    dag.assign_job_cleanup(JobCleanup(task_id="cleanup",
                                      outputs=dag.get_output_list(),
                                      dag=dag))
    return dag
