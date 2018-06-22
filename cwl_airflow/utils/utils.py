import os
import glob
import urllib.parse
import logging
import shutil
import errno
import ruamel.yaml as yaml
from airflow import configuration
from airflow.exceptions import AirflowConfigException
from airflow.models import DagRun
from airflow.utils.state import State


def shortname(n):
    return n.split("#")[-1]


def load_job(job_file):
    with open(job_file, 'r') as input_stream:
        return yaml.safe_load(input_stream)


def open_file(filename):
    """Returns list of lines from the text file. \n at the end of the lines are trimmed. Empty lines are excluded"""
    lines = []
    with open(filename, 'r') as infile:
        for line in infile:
            if line.strip():
                lines.append(line.strip())
    return lines


def export_to_file (output_filename, data):
    with open(output_filename, 'w') as output_file:
        output_file.write(data)


def get_folder(abs_path, permissions=0o0775, exist_ok=True):
    os.makedirs(abs_path, mode=permissions, exist_ok=exist_ok)
    return abs_path


def list_files(abs_path, ext=[None]):
    all_files = []
    for root, dirs, files in os.walk(abs_path):
        all_files.extend([os.path.join(root, filename) for filename in files
                          if not ext or os.path.splitext(filename)[1] in ext])
    return all_files


def flatten(input_list):
    result = []
    for i in input_list:
        if isinstance(i,list): result.extend(flatten(i))
        else: result.append(i)
    return result


def url_shortname(inputid):
    d = urllib.parse.urlparse(inputid)
    if d.fragment:
        return d.fragment.split(u"/")[-1]
    else:
        return d.path.split(u"/")[-1]


def conf_get_default (section, key, default):
    try:
        return configuration.get(section, key)
    except AirflowConfigException:
        return default


def set_permissions (item, dir_perm=0o0777, file_perm=0o0666, grp_own=os.getgid(), user_own=-1):
    os.chown(item, user_own, grp_own)
    if os.path.isfile(item):
        os.chmod(item, file_perm)
    else:
        os.chmod(item, dir_perm)
        for root, dirs, files in os.walk(item):
            for file in files:
                os.chmod(os.path.join(root,file), file_perm)
                os.chown(os.path.join(root,file), user_own, grp_own)
            for directory in dirs:
                os.chmod(os.path.join(root,directory), dir_perm)
                os.chown(os.path.join(root,directory), user_own, grp_own)


def gen_dag_id (workflow_file, job_file):
    workflow = ".".join(workflow_file.split("/")[-1].split(".")[0:-1])
    job = ".".join(job_file.split("/")[-1].split(".")[0:-1])
    return "_".join([workflow, job, load_job(job_file)["uid"].replace("-", "_")])


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


def set_logger():
    cwl_logger = logging.getLogger("cwltool")
    cwl_logger.addHandler(logging.StreamHandler())
    cwl_logger.setLevel(eval_log_level(conf_get_default('cwl','LOG_LEVEL','INFO').upper()))


def get_latest_log(dag_id, task_id="cleanup", state=State.SUCCESS):
    log_base = os.path.expanduser(configuration.get('core', 'BASE_LOG_FOLDER'))
    dag_run = sorted(DagRun.find(dag_id, state=state), reverse=True, key=lambda x: x.execution_date)[0]
    for task in dag_run.get_task_instances():
        if task.task_id == task_id:
            return f"{log_base}/{task.dag_id}/{task.task_id}/{task.execution_date.isoformat()}/{task._try_number}.log"


def get_workflow_output(dag_id):
    found_output = False
    results = []
    for line in open_file(get_latest_log(dag_id)):
        if 'WORKFLOW RESULTS' in line:
            found_output = True
            continue
        if found_output:
            results.append(line.split('Subtask: ')[1])
    return "\n".join(results)


def update_config(current_conf):
    current_conf.set('core', 'dags_are_paused_at_creation', 'False')
    current_conf.set('core', 'load_examples', 'False')
    # set default [cwl] section if it doesn't exist
    if not current_conf.conf.has_section('cwl'):
        current_conf.conf.add_section('cwl')
        current_conf.set('cwl', 'cwl_workflows', os.path.abspath(os.path.join(current_conf.get('core', 'airflow_home'), 'cwl', 'workflows')))
        current_conf.set('cwl', 'cwl_jobs', os.path.abspath(os.path.join(current_conf.get('core', 'airflow_home'), 'cwl', 'jobs')))
        current_conf.set('cwl', 'output_folder', os.path.abspath(os.path.join(current_conf.get('core', 'airflow_home'), 'cwl', 'output')))
        current_conf.set('cwl', 'tmp_folder', os.path.abspath(os.path.join(current_conf.get('core', 'airflow_home'), 'cwl', 'tmp')))
        current_conf.set('cwl', 'max_jobs_to_run', '2')
        current_conf.set('cwl', 'log_level', 'ERROR')
        current_conf.set('cwl', 'strict', 'False')


def copy_cwl_dag(current_conf):
    current_folder = os.path.dirname (__file__)
    cwl_dag_folder = os.path.join(current_conf.get('core', 'dags_folder'), os.path.basename(current_folder))  # dags_folder/cwl_airflow
    if os.path.exists(cwl_dag_folder):
        shutil.rmtree(cwl_dag_folder)
    shutil.copytree(current_folder, cwl_dag_folder, ignore=shutil.ignore_patterns('*.pyc', 'main.py', 'git_version'))
    set_permissions(cwl_dag_folder, dir_perm=0o0775, file_perm=0o0664)


def create_folders(current_conf):
    """
    Creates all required for cwl folders.
    If there is a problem not related to already existing folder - raise exception
    :param current_conf: airflow configuration ConfigParser
    :return: None
    """
    folder_list = []
    folder_list.append(current_conf.get('cwl', 'cwl_workflows'))
    folder_list.append(current_conf.get('cwl', 'output_folder'))
    folder_list.append(current_conf.get('cwl', 'tmp_folder'))
    folder_list.append(os.path.join(current_conf.get('cwl', 'cwl_jobs'), 'new'))
    folder_list.append(os.path.join(current_conf.get('cwl', 'cwl_jobs'), 'running'))
    folder_list.append(os.path.join(current_conf.get('cwl', 'cwl_jobs'), 'success'))
    folder_list.append(os.path.join(current_conf.get('cwl', 'cwl_jobs'), 'fail'))
    for folder in folder_list:
        try:
            os.makedirs(folder)
            set_permissions(folder, dir_perm=0o0775, file_perm=0o0664)
        except OSError as ex:
            if ex.errno != errno.EEXIST:
                raise  # raises the error again if it wasn't a problem of already existed folder