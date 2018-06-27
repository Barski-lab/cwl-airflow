import os
import urllib.parse
import logging
import argparse
from schema_salad.ref_resolver import Loader
from cwltool.load_tool import jobloaderctx
from airflow import configuration
from airflow.exceptions import AirflowConfigException
from airflow.models import DagRun
from airflow.utils.state import State


def normalize_args(args, skip_list=[]):
    """Converts all relative path arguments to absolute ones relatively to the current working directory"""
    normalized_args = {}
    for key, value in args.__dict__.items():
        if key not in skip_list:
            normalized_args[key] = value if not value or os.path.isabs(value) else os.path.normpath(os.path.join(os.getcwd(), value))
        else:
            normalized_args[key]=value
    return argparse.Namespace(**normalized_args)


def shortname(n):
    return n.split("#")[-1]


def load_job(job_file):
    loader = Loader(jobloaderctx.copy())
    job_order_object, _ = loader.resolve_ref(job_file, checklinks=False)
    return job_order_object


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
            kwargs = {"log_base": log_base,
                      "dag_id": task.dag_id,
                      "task_id": task.task_id,
                      "execution_date": task.execution_date.isoformat(),
                      "try_number": task._try_number
            }
            return "{log_base}/{dag_id}/{task_id}/{execution_date}/{try_number}.log".format(**kwargs)


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
