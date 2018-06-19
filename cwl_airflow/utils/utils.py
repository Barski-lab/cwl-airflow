import os
import glob
import urllib.parse
import logging
import shutil
import errno
import tempfile
import re
import ruamel.yaml as yaml
from datetime import datetime
from airflow import configuration
from airflow.exceptions import AirflowConfigException


def shortname(n):
    return n.split("#")[-1]


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


def get_only_files (jobs, key, excl_key = None):
    key_filtered = []
    for item in jobs:
        key_filtered.extend(\
                            [ filename for filename in glob.iglob(item[key]+"/*") if \
                                    (not excl_key and os.path.isfile(filename)) or \
                                    (excl_key and os.path.isfile(filename) and \
                                     os.path.basename(filename) not in [os.path.basename(excl_filename) for excl_filename in glob.iglob(item[excl_key]+"/*")])\
                                    ]\
                            )                              
    return key_filtered


def get_uid (job_file):
    with open(job_file, 'r') as input_stream:
        job = yaml.safe_load(input_stream)
    return job.get("uid", '.'.join(job_file.split("/")[-1].split('.')[0:-1]))


def create_backup_args(args, filename):
    del args['func']  # When creating backup we don't need func to be included
    with open(os.path.join(os.getcwd(), filename), 'w') as backup_file:
        yaml.safe_dump(args, stream=backup_file)


def remove_backup_args(filename):
    os.remove(os.path.join(os.getcwd(), filename))


def read_backup_args(filename):
    with open(os.path.join(os.getcwd(), filename), 'r') as backup_file:
        return yaml.safe_load(backup_file)


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
    return ".".join(workflow_file.split("/")[-1].split(".")[0:-1]) + "-" + get_uid(job_file) + "-" + datetime.fromtimestamp(os.path.getctime(job_file)).isoformat().replace(':', '-')


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
    print (results.rstrip('\n'))


def create_output_folder (args, job_entry, job, workflow_file):
    if not args.get('outdir'):
        if args.get('ignore_def_outdir'):
            default_outdir = os.path.join(conf_get_default('cwl', 'OUTPUT_FOLDER', os.getcwd()), gen_dag_id(workflow_file,job))
        else:
            default_outdir = os.path.abspath(os.getcwd())
        output_folder = job_entry.get('output_folder', default_outdir)
        output_folder = output_folder if os.path.isabs(output_folder) else os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(job)), output_folder))
    else:
        output_folder = os.path.abspath(args.get('outdir'))
    os.makedirs(output_folder, mode=0o0775, exist_ok=True)
    return output_folder


def create_tmp_folder (args, job_entry, job):
    if not args.get('tmp_folder'):
        tmp_folder = job_entry.get('tmp_folder', conf_get_default('cwl', 'TMP_FOLDER', tempfile.mkdtemp()))
        tmp_folder = tmp_folder if os.path.isabs(tmp_folder) else os.path.normpath(os.path.join(os.path.dirname(job), tmp_folder))
    else:
        tmp_folder = os.path.abspath(args.get('tmp_folder'))
    os.makedirs(tmp_folder, mode=0o0775, exist_ok=True)
    return tmp_folder


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


def find_workflow(job_filename):
    workflows_folder = configuration.get('biowardrobe', 'workflows')
    all_workflows = {}
    for root, dirs, files in os.walk(workflows_folder):
        all_workflows.update( \
                              { filename: os.path.join(root, filename) \
                                for filename in files \
                                if  os.path.splitext(filename)[1] == '.cwl' \
                                    and (filename not in all_workflows \
                                                 or os.path.getctime(os.path.join(root, filename)) < \
                                                 os.path.getctime( all_workflows[filename]) ) \
                              } \
                            )
    for key in sorted(all_workflows, key=len, reverse=True):
        if re.match(os.path.splitext(key)[0], os.path.basename(job_filename)):
            return all_workflows[key]