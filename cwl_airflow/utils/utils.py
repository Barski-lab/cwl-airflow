import os
import sys
import urllib.parse
import logging
import argparse
import re
from json import dumps
import cwltool.context
from cwltool.workflow import default_make_tool
from cwltool.resolver import tool_resolver
import cwltool.load_tool as load
from cwltool.argparser import get_default_args
from cwl_airflow.utils.mute import Mute
from schema_salad.ref_resolver import Loader
from airflow import configuration
from airflow.exceptions import AirflowConfigException
from airflow.models import DagRun


def norm_path(path):
    return os.path.abspath(os.path.normpath(os.path.normcase(path)))


def get_files(current_dir, filename_pattern=".*"):
    """Files with the identical basenames are overwritten"""
    files_dict = {}
    for root, dirs, files in os.walk(current_dir):
        files_dict.update(
            {filename: os.path.join(root, filename) for filename in files if re.match(filename_pattern, filename)}
        )
    return files_dict


def convert_to_workflow(tool, tool_file, workflow_file):
    workflow = {"cwlVersion": "v1.0",
                "class":      "Workflow",
                "inputs":     gen_inputs(tool),
                "outputs":    gen_outputs(tool)}
    workflow["steps"] = [{"run": tool_file,
                          "in": [{"source": inp["id"], "id": inp["id"]} for inp in workflow["inputs"]],
                          "out": [outp["id"] for outp in workflow["outputs"]],
                          "id": "static_step"}]
    if tool.get("$namespaces", None):
        workflow["$namespaces"] = tool["$namespaces"]
    if tool.get("$schemas", None):
        workflow["$schemas"] = tool["$schemas"]
    if tool.get("requirements", None):
        workflow["requirements"] = tool["requirements"]

    with open(workflow_file, 'w') as output_stream:
        output_stream.write(dumps(workflow, indent=4))

    return workflow_file


def gen_inputs(tool):
    inputs = []
    for inpt in tool["inputs"]:
        custom_input = {}
        if inpt.get("id", None):
            custom_input["id"] = shortname(inpt["id"])
        if inpt.get("type", None):
            custom_input["type"] = inpt["type"]
        if inpt.get("format", None):
            custom_input["format"] = inpt["format"]
        if inpt.get("doc", None):
            custom_input["doc"] = inpt["doc"]
        if inpt.get("label", None):
            custom_input["label"] = inpt["label"]
        inputs.append(custom_input)
    return inputs


def gen_outputs(tool):
    outputs = []
    for outp in tool["outputs"]:
        custom_output = {}
        if outp.get("id", None):
            custom_output["id"] = shortname(outp["id"])
        if outp.get("type", None):
            custom_output["type"] = outp["type"]
        if outp.get("format", None):
            custom_output["format"] = outp["format"]
        if outp.get("doc", None):
            custom_output["doc"] = outp["doc"]
        if outp.get("label", None):
            custom_output["label"] = outp["label"]
        if outp.get("id", None):
            custom_output["outputSource"] = "static_step/" + shortname(outp["id"])
        outputs.append(custom_output)
    return outputs


def load_cwl(cwl_file):
    load.loaders = {}
    loading_context = cwltool.context.LoadingContext(get_default_args())
    loading_context.construct_tool_object = default_make_tool
    loading_context.resolver = tool_resolver
    return load.load_tool(cwl_file, loading_context)


def exit_if_unsupported_feature(cwl_file, exit_code=33):
    with Mute():
        tool = load_cwl(cwl_file).tool
    if tool["class"] == "Workflow" and [step["id"] for step in tool["steps"] if "scatter" in step]:
        logging.warning("Failed to submit workflow\n- {} - scatter is not supported".format(cwl_file))
        sys.exit(exit_code)


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
    loader = Loader(load.jobloaderctx.copy())
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


def gen_dag_id(job_file):
    job_content = load_job(job_file)
    w_seg = ".".join(job_content["workflow"].split("/")[-1].split(".")[0:-1])
    j_seg = ".".join(job_file.split("/")[-1].split(".")[0:-1])
    return "-".join([w_seg, j_seg, job_content["uid"]])


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


def get_latest_log(dag_id, task_id="JobCleanup", state=None):
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


def get_workflow_output(dag_id):  # make something more relyable that splitting by Subtask
    logging.info("Workflow results")
    found_output = False
    results = []
    for line in open_file(get_latest_log(dag_id)):
        if 'WORKFLOW RESULTS' in line:
            found_output = True
            continue
        if found_output:
            try:
                results.append(line.split('Subtask: ')[1])
            except Exception:  # Better use IndexError instead of Exception
                pass
    return "\n".join(results)
