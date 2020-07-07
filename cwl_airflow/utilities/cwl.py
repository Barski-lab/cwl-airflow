import os
import sys
import dill as pickle  # standard pickle doesn't handle lambdas
import argparse
import json
import errno
import shutil

from uuid import uuid4
from copy import deepcopy
from jsonmerge import merge
from urllib.parse import urlsplit
from typing import MutableMapping, MutableSequence
from ruamel.yaml.comments import CommentedMap
from airflow.configuration import (
    AIRFLOW_HOME,
    conf
)
from airflow.exceptions import AirflowConfigException
from cwltool.argparser import get_default_args
from cwltool.main import (
    setup_loadingContext,
    init_job_order
)
from cwltool.context import (
    LoadingContext,
    RuntimeContext
)
from cwltool.process import relocateOutputs
from cwltool.load_tool import (
    load_tool,
    jobloaderctx
)
from cwltool.executors import SingleJobExecutor
from cwltool.utils import visit_class
from cwltool.mutation import MutationManager
from schema_salad.ref_resolver import Loader
from schema_salad.exceptions import SchemaSaladException
from schema_salad.ref_resolver import file_uri

from cwl_airflow.utilities.helpers import (
    get_md5_sum,
    get_dir,
    get_path_from_url,
    load_yaml,
    dump_json,
    get_absolute_path,
    get_rootname,
    remove_field_from_dict
)


CWL_TMP_FOLDER = os.path.join(AIRFLOW_HOME, "cwl_tmp_folder")
CWL_OUTPUTS_FOLDER = os.path.join(AIRFLOW_HOME, "cwl_outputs_folder")
CWL_PICKLE_FOLDER = os.path.join(AIRFLOW_HOME, "cwl_pickle_folder")
CWL_USE_CONTAINER = True
CWL_NO_MATCH_USER = False
CWL_SKIP_SCHEMAS = True
CWL_STRICT = False
CWL_QUIET = False
CWL_RM_TMPDIR = True       # better not to change without need
CWL_MOVE_OUTPUTS = "move"  # better not to change without need


DAG_TEMPLATE="""#!/usr/bin/env python3
from cwl_airflow.extensions.cwldag import CWLDAG
dag = CWLDAG(workflow="{0}", dag_id="{1}")
"""


def conf_get(section, key, default):
    """
    Return value from AirflowConfigParser object.
    If section or key is absent, return default
    """

    try:
        return conf.get(section, key)
    except AirflowConfigException:
        return default


def collect_reports(context, cwl_args, task_ids=None):
    """
    Collects reports from "context" for specified "task_ids".
    If "task_ids" was not set, use all tasks from DAG.
    Loads and merges data from reports.
    """

    task_ids = context["dag"].task_ids if task_ids is None else task_ids

    job_data = {}
    for report_location in context["ti"].xcom_pull(task_ids=task_ids):
        if report_location is not None:
            report_data = load_job(
                cwl_args,                 # should be ok even if cwl_args["workflow"] points to the original workflow
                report_location           # as all defaults from it should have been already added by dispatcher
            )
            job_data = merge(job_data, report_data)
    
    return job_data


def get_default_cwl_args(preset_cwl_args=None):
    """
    Returns default arguments required by cwltool's functions with a few
    parameters added and overwritten (required by CWL-Airflow). Defaults
    can be preset through "preset_cwl_args" if provided. All new fields
    from "preset_cwl_args" will be added to the returned results.
    """

    preset_cwl_args = {} if preset_cwl_args is None else deepcopy(preset_cwl_args)

    # default arguments required by cwltool
    required_cwl_args = get_default_args()

    # update default arguments required by cwltool with those that were preset by user
    required_cwl_args.update(preset_cwl_args)

    # update default arguments required by cwltool with those that might
    # be updated based on the higher priority of airflow configuration
    # file. If airflow configuration file doesn't include correspondent
    # parameters, use those that were preset by user, or defaults
    required_cwl_args.update(
        {
            "tmp_folder": get_dir(
                conf_get(
                    "cwl", "tmp_folder",
                    preset_cwl_args.get("tmp_folder", CWL_TMP_FOLDER)
                )
            ),
            "outputs_folder": get_dir(                                             # for CWL-Airflow to store outputs if "outputs_folder" is not overwritten in job
                conf_get(
                    "cwl", "outputs_folder",
                    preset_cwl_args.get("outputs_folder", CWL_OUTPUTS_FOLDER)
                )
            ),
            "pickle_folder": get_dir(                                              # for CWL-Airflow to store pickled workflows
                conf_get(
                    "cwl", "pickle_folder",
                    preset_cwl_args.get("pickle_folder", CWL_PICKLE_FOLDER)
                )
            ),
            "use_container": conf_get(
                "cwl", "use_container",
                preset_cwl_args.get("use_container", CWL_USE_CONTAINER)            # execute jobs in a docker containers
            ),
            "no_match_user": conf_get(
                "cwl", "no_match_user",
                preset_cwl_args.get("no_match_user", CWL_NO_MATCH_USER)            # disables passing the current uid to "docker run --user"
            ),
            "skip_schemas": conf_get(
                "cwl", "skip_schemas", 
                preset_cwl_args.get("skip_schemas", CWL_SKIP_SCHEMAS)              # it looks like this doesn't influence anything in the latest cwltool
            ),
            "strict": conf_get(
                "cwl", "strict", 
                preset_cwl_args.get("strict", CWL_STRICT)
            ),
            "quiet": conf_get(
                "cwl", "quiet", 
                preset_cwl_args.get("quiet", CWL_QUIET)
            ),
            "rm_tmpdir": preset_cwl_args.get("rm_tmpdir", CWL_RM_TMPDIR),          # even if we can set it in "preset_cwl_args" it's better not to change
            "move_outputs": preset_cwl_args.get("move_outputs", CWL_MOVE_OUTPUTS), # even if we can set it in "preset_cwl_args" it's better not to change
            "enable_dev": True                                                     # TODO: fails to run without it when creating workflow from tool. Ask Peter? 
        }
    )

    return required_cwl_args


def relocate_outputs(cwl_args, job_data, remove_tmp_folder=None):
    """
    Maps workflow outputs back to normal (from step_id_step_out to
    workflow output) and filters "job_data" based on them (combining
    items from "job_data" into a list based on "outputSource" if it
    was a list).
    Relocates filtered outputs to "outputs_folder" and, by default,
    removes tmp_folder, unless "remove_tmp_folder" is set to something
    else. Saves report with relocated outputs as "workflow_report.json" to
    "outputs_folder"
    """
    
    remove_tmp_folder = True if remove_tmp_folder is None else remove_tmp_folder

    cwl_args_copy = deepcopy(cwl_args)
    job_data_copy = deepcopy(job_data)

    workflow_tool = fast_cwl_load(cwl_args_copy)

    # Filter "job_data" to include only items required by workflow outputs.
    # Remap keys to the proper workflow outputs IDs (without step id).
    # If "outputSource" was a list even of len=1, find all correspondent items
    # from the "job_data" and assign them as list of the same size. 

    filtered_job_data = {}
    for output_id, output_data in get_items(workflow_tool["outputs"]):
        collected_job_items = []
        for source_id, _ in get_items(output_data["outputSource"]):
            collected_job_items.append(
                job_data_copy[source_id.replace("/", "_")]
            )
        if isinstance(output_data["outputSource"], list):
            filtered_job_data[output_id] = collected_job_items
        else:
            filtered_job_data[output_id] = collected_job_items[0]

    # Outputs will be always copied, because source_directories=[]

    runtime_context = RuntimeContext(cwl_args_copy)
    relocated_job_data = relocateOutputs(
        outputObj=filtered_job_data,
        destination_path=job_data_copy["outputs_folder"],
        source_directories=[],                              # use it as a placeholder (shouldn't influence anything)
        action=runtime_context.move_outputs,
        fs_access=runtime_context.make_fs_access(""),
        compute_checksum=runtime_context.compute_checksum,
        path_mapper=runtime_context.path_mapper
    )

    # Dump report with relocated outputs

    workflow_report = os.path.join(
        job_data_copy["outputs_folder"],
        "workflow_report.json"
    )

    dump_json(relocated_job_data, workflow_report)

    # Clean "tmp_folder"

    if remove_tmp_folder:
        shutil.rmtree(job_data_copy["tmp_folder"], ignore_errors=False)

    return relocated_job_data, workflow_report


def execute_workflow_step(
    cwl_args,
    job_data,
    task_id,
    executor=None
):

    executor = SingleJobExecutor() if executor is None else executor
    
    cwl_args_copy = deepcopy(cwl_args)

    step_tmp_folder, step_cache_folder, step_outputs_folder, step_report = get_temp_folders(task_id, job_data)

    cwl_args_copy.update({
        "tmp_outdir_prefix": step_cache_folder + "/",
        "tmpdir_prefix": step_cache_folder + "/",
        "cidfile_dir": step_tmp_folder,
        "cidfile_prefix": task_id,
        "basedir": os.getcwd(),            # job should have abs path for inputs, so this is useless
        "outdir": step_outputs_folder
    })
    
    workflow_step_path = os.path.join(step_tmp_folder, task_id + "_step_workflow.cwl")
    fast_cwl_step_load(cwl_args_copy, task_id, workflow_step_path)
    cwl_args_copy["workflow"] = workflow_step_path
    
    _stderr = sys.stderr                   # to trick the logger
    sys.stderr = sys.__stderr__
    step_outputs, step_status = executor(
        slow_cwl_load(cwl_args_copy),
        job_data,
        RuntimeContext(cwl_args_copy)
    )
    sys.stderr = _stderr

    if step_status != "success":
        raise ValueError

    # To remove "http://commonwl.org/cwltool#generation": 0
    # (copied from cwltool)
    visit_class(step_outputs, ("File",), MutationManager().unset_generation)

    dump_json(step_outputs, step_report)

    return step_outputs, step_report


def get_temp_folders(task_id, job_data):

    step_tmp_folder = get_dir(
        os.path.join(
            job_data["tmp_folder"],
            task_id
        )
    )

    step_cache_folder = get_dir(
        os.path.join(
            step_tmp_folder,
            task_id + "_step_cache"
        )
    )


    step_outputs_folder = get_dir(
        os.path.join(
            step_tmp_folder,
            task_id + "_step_outputs"
        )
    )

    step_report = os.path.join(
        step_tmp_folder,
        task_id + "_step_report.json"
    )

    return step_tmp_folder, step_cache_folder, step_outputs_folder, step_report


def load_job(cwl_args, job, cwd=None):
    """
    Follows standard routine for loading job order object file
    the same way as cwltool does it. "cwl_args" should include
    "workflow" field.

    If "cwl_args" is string, assume it's the path to the wokrflow.
    If path is relative, it will be resolved based on "cwd" or
    current working directory (if "cwd" is None). Default arguments
    required for cwltool's functions will be generated and workflow
    will be loaded.

    Tries to load json object from file. If failed, assumes that
    "job" has been already parsed into Object. Inits loaded
    job_data based on the workflow provided in the "workflow"
    field of cwl_args["cwl"] (mostly for setting defaults from
    the workflow; never fails)

    If job was file, resolves relative paths based on the job file
    location. If job was already parsed Object and "cwd" is not None,
    then relative paths will be resolved based on "cwd". Otherwise,
    relative paths will not be resolved.

    Checks links only when relative paths are resolved, failing on
    missing input files.
    
    Always returns CommentedMap
    """

    job_copy = deepcopy(job)

    # check if instead of proper cwl_args we provided path to the workflow
    if isinstance(cwl_args, str):
        cwl_args_copy = get_default_cwl_args(
            {
                "workflow": get_absolute_path(cwl_args, cwd)
            }
        )
    else:
        cwl_args_copy = deepcopy(cwl_args)

    loading_context = setup_loadingContext(
        LoadingContext(cwl_args_copy),
        RuntimeContext(cwl_args_copy),
        argparse.Namespace(**cwl_args_copy)
    )

    try:
        job_data, _ = loading_context.loader.resolve_ref(job_copy, checklinks=True)
    except (FileNotFoundError, SchemaSaladException) as err:
        job_data = load_yaml(json.dumps(job_copy))
        if cwd is not None:
            job_data["id"] = file_uri(cwd) + "/"
            job_data, metadata = loading_context.loader.resolve_all(
                job_data,
                job_data["id"],
                checklinks=True
            )

    workflow_tool = slow_cwl_load(cwl_args_copy)

    initialized_job_data = init_job_order(
        job_order_object=job_data,
        args=argparse.Namespace(**cwl_args_copy),
        process=workflow_tool,
        loader=loading_context.loader,
        stdout=os.devnull  # TODO: maybe it's better to use stdout or some logger?
    )

    return initialized_job_data


def fast_cwl_step_load(cwl_args, target_id, location=None):
    """
    "cwl_args" should include "pickle_folder" and "workflow".
    Other args are required for a proper LoadingContext
    and RuntimeContext construction when calling "slow_cwl_load"
    from "fast_cwl_load"

    Constructs workflow from a single step selected by its id.
    Other steps are removed. Workflow inputs and outputs are
    updated based on source fields of "in" and "out" from the
    selected workflow step. IDs of updated workflow inputs and
    outputs as well as IDs of correspondent "source" fields
    also include step id separated by underscore. All other
    fields remain unchanged.

    Returned value is always CommentedMap with parsed tool.
    If "location" is not None, export modified workflow.
    """

    cwl_args_copy = deepcopy(cwl_args)

    workflow_inputs = []
    workflow_outputs = []
    workflow_steps = []

    workflow_tool = fast_cwl_load(cwl_args_copy)

    selected_step = list(get_items(workflow_tool["steps"], target_id))[0][1]

    workflow_steps.append(selected_step)

    for _, step_in in get_items(selected_step.get("in", [])):           # step might not have "in"
        
        updated_sources = []  # to keep track of updated sources

        for step_in_source, _ in get_items(step_in.get("source", [])):  # "in" might not have "source"

            try:

                # try to find workflow input that corresponds to "source"

                workflow_input = list(get_items(
                    workflow_tool["inputs"],
                    step_in_source
                ))[0][1]

                updated_workflow_input = {
                    "id": step_in_source,
                    "type": workflow_input["type"]
                }

                if "default" in workflow_input:
                    updated_workflow_input["default"] = workflow_input["default"]
                
                # Check if we have already added input based on the same "source"
                # from another item from "in". Skip adding the same input twice.

                if len(list(get_items(workflow_inputs, step_in_source))) == 0:
                    workflow_inputs.append(updated_workflow_input)

                updated_sources.append(step_in_source)

            except (IndexError, KeyError):
                
                # Need to find upstream step that corresponds to "source"

                upstream_step = list(get_items(
                    workflow_tool["steps"],
                    get_short_id(step_in_source, only_step_name=True)
                ))[0][1]

                # Need to load tool from "run" of the found upstream step
                # and look for the output that corresponds to "source".
                # We look for correspondence only based on "id"

                cwl_args_copy["workflow"] = upstream_step["run"]
                upstream_step_tool = fast_cwl_load(cwl_args_copy)

                upstream_step_output = list(get_items(
                    {get_short_id(k, only_id=True): v for k, v in get_items(upstream_step_tool["outputs"])},  # trick
                    get_short_id(step_in_source, only_id=True)
                ))[0][1]

                step_in_source_with_step_id = step_in_source.replace("/", "_")  # to include both step name and id

                updated_workflow_input = {
                    "id": step_in_source_with_step_id,  
                    "type": upstream_step_output["type"]
                }

                # Check if we have already added input based on the same "source"
                # from another item from "in". Skip adding the same input twice.

                if len(list(get_items(workflow_inputs, step_in_source_with_step_id))) == 0:
                    workflow_inputs.append(updated_workflow_input)
                
                updated_sources.append(step_in_source_with_step_id)

        # replace "source" in step's "in" if anything was updated
        if len(updated_sources) > 0:
            if isinstance(step_in["source"], list):
                step_in["source"] = updated_sources
            else:
                step_in["source"] = updated_sources[0]   

    # Need to load tool from the "run" field of the selected step
    # and look for the outputs that correspond to the items from "out".
    # We look for correspondence only based on "id"

    cwl_args_copy["workflow"] = selected_step["run"]
    selected_step_tool = fast_cwl_load(cwl_args_copy)

    for step_out, _ in get_items(selected_step["out"]):
        selected_step_output = list(get_items(
            {get_short_id(k, only_id=True): v for k, v in get_items(selected_step_tool["outputs"])},  # trick
            get_short_id(step_out, only_id=True)
        ))[0][1]
        step_out_with_step_id = step_out.replace("/", "_")  # to include both step name and id
        workflow_outputs.append({
            "id": step_out_with_step_id,
            "type": selected_step_output["type"],
            "outputSource": step_out
        })

    workflow_tool.update(
        {
            "inputs": workflow_inputs,
            "outputs": workflow_outputs,
            "steps": workflow_steps
        }
    )

    if location is not None:
        dump_json(workflow_tool, location)

    return workflow_tool


def get_items(data, target_id=None):
    """
    If data is dictionary returns [(key, value)].
    
    If data is string return [key, data].
    
    If data is list of items returns [(key, value)] with key set
    from item["id"] and value equal to the item itself.

    If items are strings, set keys from this strings and return [(key, item)].
    
    For all other cases return either list of tuples of unchanged items or
    tuple with unchanged input data.
    
    Keys are always shortened to include only part after symbol #

    If target_id is set, filter outputs by key == target_id if
    found. Otherwise return []
    """

    if isinstance(data, MutableMapping):
        for key, value in data.items():
            if target_id is not None:
                if key == target_id or get_short_id(key) == target_id:
                    yield get_short_id(key), value 
                else:
                    continue
            else:
                yield get_short_id(key), value 
    elif isinstance(data, MutableSequence):
        for item in data:
            if isinstance(item, str):
                if target_id is not None:
                    if item == target_id or get_short_id(item) == target_id:
                        yield get_short_id(item), item
                    else:
                        continue
                else:
                    yield get_short_id(item), item
            elif "id" in item:  # we checked that item wasn't string, so "id" is not substring of "item"
                if target_id is not None:
                    if item["id"] == target_id or get_short_id(item["id"]) == target_id:
                        yield get_short_id(item["id"]), item
                    else:
                        continue
                else:
                    yield get_short_id(item["id"]), item
            else:
                if target_id is not None:
                    if item == target_id:
                        yield item, item
                    else:
                        pass  # do not yield anything
                else:
                    yield item, item
    elif isinstance(data, str):
        if target_id is not None:
            if data == target_id or get_short_id(data) == target_id:
                yield get_short_id(data), data
            else:
                pass  # do not yield anything
        else:
            yield get_short_id(data), data
    else:
        if target_id is not None:
            if data == target_id:
                yield data, data
            else:
                pass  # do not yield anything
        else:
            yield data, data


def get_short_id(long_id, only_step_name=None, only_id=None):
    """
    Shortens long id to include only part after symbol #.
    If # is not present, use long_id. If only_step_name is True,
    return a short step name. If only_id is True, return a short
    id without step name. If part after symbol # includes three
    sections separated by "/", discard the middle one. If part
    after symbol # includes only one section separated by "/",
    reset "only_step_name" and "only_id" to False as we don't
    know whether it was step name of "id"
    """
    fragment = urlsplit(long_id).fragment
    part = fragment if fragment != "" else long_id

    if len(part.split("/")) == 3:                                  # if "id" has weird uid between step name and id
        part = "/".join([part.split("/")[0], part.split("/")[2]])

    if len(part.split("/")) == 1:                                  # if fragment is only one word (based on "/")
        only_step_name, only_id = False, False

    part = part.split("/")[0] if only_step_name else part
    part = "/".join(part.split("/")[1:]) if only_id else part
    return part


def fast_cwl_load(cwl_args):
    """
    Tries to load pickled version of CWL file from the
    pickle_folder. Uses md5 sum as a basename for the file.
    If file not found or failed to unpickle, load CWL data
    from the workflow file and save pickled version.

    "cwl_args" should include "pickle_folder" and "workflow".
    Other args are required for a proper LoadingContext
    and RuntimeContext construction when calling "slow_cwl_load".

    Returned value is always CommentedMap with parsed tool, because
    "slow_cwl_load" is always called with reduced=True. Dill will fail
    to pickle/unpickle the whole workflow.

    If "workflow" was already parsed into CommentedMap, return it
    unchanged. Nothing will be pickled
    """
    cwl_args_copy = deepcopy(cwl_args)

    if isinstance(cwl_args_copy["workflow"], CommentedMap):
        return cwl_args_copy["workflow"]

    pickled_workflow = os.path.join(
        cwl_args_copy["pickle_folder"],
        get_md5_sum(cwl_args_copy["workflow"]) + ".p"  # no need to use get_path_from_url
    )

    try:
        with open(pickled_workflow, "rb") as input_stream:
            workflow_tool = pickle.load(input_stream)
    except (FileNotFoundError, pickle.UnpicklingError) as err:
        workflow_tool = slow_cwl_load(cwl_args_copy, True)
        with open(pickled_workflow , "wb") as output_stream:
            pickle.dump(workflow_tool, output_stream)

    return workflow_tool


def slow_cwl_load(cwl_args, reduced=False):
    """
    Follows standard routine for loading CWL file
    the same way as cwltool does it. cwl_args should
    include "workflow" field. If "reduced" is
    True, return only tool (useful for pickling,
    because the whole Workflow object fails to be
    unpickled).
    If "workflow" was already parsed into CommentedMap,
    return it unchanged (similar to what we can get if
    "reduced" was True)
    """

    cwl_args_copy = deepcopy(cwl_args)

    if isinstance(cwl_args_copy["workflow"], CommentedMap):
        return cwl_args_copy["workflow"]

    if not os.path.isfile(get_path_from_url(cwl_args_copy["workflow"])):        # need to get rid of file:// if it was url
        raise FileNotFoundError(
            errno.ENOENT, os.strerror(errno.ENOENT), cwl_args_copy["workflow"]
        )

    workflow_data = load_tool(
        cwl_args_copy["workflow"],               # no need to use get_path_from_url
        setup_loadingContext(
            LoadingContext(cwl_args_copy),
            RuntimeContext(cwl_args_copy),
            argparse.Namespace(**cwl_args_copy)
        )
    )

    return workflow_data.tool if reduced else workflow_data


# Not used at all
def embed_all_runs(
    workflow_tool,
    cwl_args
):
    """
    Tries to find and load all "run" fields from the workflow_tool.
    Updates "workflow_tool" in place.
    """

    cwl_args_copy = deepcopy(cwl_args)

    if isinstance(workflow_tool, MutableSequence):
        for item in workflow_tool:
            embed_all_runs(item, cwl_args_copy)
    elif isinstance(workflow_tool, MutableMapping):
        if "run" in workflow_tool and isinstance(workflow_tool["run"], str):
            cwl_args_copy["workflow"] = workflow_tool["run"]
            workflow_tool["run"] = slow_cwl_load(cwl_args_copy, reduced=True)
        for item in workflow_tool.values():
            embed_all_runs(item, cwl_args_copy)


def convert_to_workflow(command_line_tool, location=None):
    """
    Converts CommandLineTool to Workflow. Copies minimum number of fields.
    If "location" is not None, dumps results to json file.
    """

    workflow_tool = {
        "class": "Workflow",
        "cwlVersion": command_line_tool["cwlVersion"]
    }

    for input_id, input_data in get_items(command_line_tool["inputs"]):
        workflow_tool.setdefault("inputs", []).append(
            {
                "id": input_id,
                "type": remove_field_from_dict(input_data["type"], "inputBinding")  # "type" in WorkflowInputParameter cannot have "inputBinding"
            }
        )

    for output_id, output_data in get_items(command_line_tool["outputs"]):
        workflow_tool.setdefault("outputs", []).append(
            {
               "id": output_id,
               "type": output_data["type"],
               "outputSource": get_rootname(command_line_tool["id"]) + "/" + output_id
            }
        )

    workflow_tool["steps"] = [
        {
            "id": get_rootname(command_line_tool["id"]),
            "run": command_line_tool,
            "in": [
                {
                    "id": input_id, "source": input_id
                } for input_id, _ in get_items(workflow_tool["inputs"])
            ],
            "out": [
                output_id for output_id, _ in get_items(workflow_tool["outputs"])
            ]
        }
    ]

    if location is not None:
        dump_json(workflow_tool, location)

    return workflow_tool
