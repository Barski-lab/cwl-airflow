import os
import re
import sys
import dill as pickle  # standard pickle doesn't handle lambdas
import argparse
import json
import zlib
import shutil
import docker
import logging
import binascii

from copy import deepcopy
from jsonmerge import merge
from urllib.parse import urlsplit
from tempfile import NamedTemporaryFile
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
    load_yaml,
    dump_json,
    get_absolute_path,
    get_rootname,
    remove_field_from_dict,
    get_uncompressed,
    get_compressed,
    get_files
)


CWL_TMP_FOLDER = os.path.join(AIRFLOW_HOME, "cwl_tmp_folder")
CWL_OUTPUTS_FOLDER = os.path.join(AIRFLOW_HOME, "cwl_outputs_folder")
CWL_INPUTS_FOLDER = os.path.join(AIRFLOW_HOME, "cwl_inputs_folder")
CWL_PICKLE_FOLDER = os.path.join(AIRFLOW_HOME, "cwl_pickle_folder")
CWL_USE_CONTAINER = True
CWL_NO_MATCH_USER = False
CWL_SKIP_SCHEMAS = True
CWL_STRICT = False
CWL_QUIET = False
CWL_RM_TMPDIR = True       # better not to change without need
CWL_MOVE_OUTPUTS = "move"  # better not to change without need
CWL_ENABLE_DEV = True      # better not to change without need


DAG_TEMPLATE="""#!/usr/bin/env python3
from cwl_airflow.extensions.cwldag import CWLDAG
dag = CWLDAG(
    workflow="{0}",
    dag_id="{1}"
)
"""


def overwrite_deprecated_dag(
    dag_location,
    deprecated_dags_folder=None
):
    """
    Loads DAG content from "dag_location" file. Searches for "dag.create()" command.
    If not found, we don't need to upgrade this DAG (it's either not from CWL-Airflow,
    or already in a new format). If "deprecated_dags_folder" is not None, copies original
    DAG file there before DAG upgrading. After copying deprecated DAG to the
    "deprecated_dags_folder" updates ".airflowignore" with DAG file basename to exclude
    it from Airflow parsing. Upgraded DAG will always include base64 encoded zlib
    compressed workflow content. In case "workflow_location" is relative path, it will
    be resolved based on the dirname of "dag_location" (useful for tests only, because
    all our old DAGs always have absolute path to the CWL file). Function doesn't backup
    or update the original CWL file.
    TODO: in case more coplicated DAG files that include "default_args", etc, this function
    should be updated to the more complex one.
    """

    with open(dag_location, "r+") as io_stream:                # open for both reading and writing

        dag_content = io_stream.read()

        if not re.search("dag\\.create\\(\\)", dag_content):   # do nothing if it wasn't old-style DAG
            return

        workflow_location = get_absolute_path(                 # resolve relative to dirname of "dag_location" (good for tests)
            re.search(
                "(cwl_workflow\\s*=\\s*[\"|'])(.+?)([\"|'])",
                dag_content
            ).group(2),
            os.path.dirname(dag_location)
        )

        dag_id = re.search(
            "(dag_id\\s*=\\s*[\"|'])(.+?)([\"|'])",
            dag_content
        ).group(2)

        compressed_workflow_content = get_compressed(
            fast_cwl_load(workflow_location)                   # no "run" embedding or convertion to Workflow. If DAG worked, cwl should be ok too
        )

        if deprecated_dags_folder is not None:                 # copy old DAG to the folder with deprecated DAGs, add ".airflowignore"
            get_dir(deprecated_dags_folder)                    # try to create "deprecated_dags_folder" if it doesn't exist
            shutil.copy(dag_location, deprecated_dags_folder)  # copy DAG file
            ignore = os.path.join(
                deprecated_dags_folder,
                ".airflowignore"
            )
            with open(ignore, "a") as output_stream:           # add deprecated DAG to ".airflowignore"
                output_stream.write(
                    os.path.basename(dag_location) + "\n"
                )

        io_stream.seek(0)                                      # rewind "dag_location" file to the beginning
        io_stream.write(
            DAG_TEMPLATE.format(
                compressed_workflow_content, dag_id
            )
        )
        io_stream.truncate()                                   # remove old data at the end of a file if anything became shorter than original


def conf_get(
    section,
    key,
    default
):
    """
    Return value from AirflowConfigParser object.
    If section or key is absent, return default.
    Suppresses annoying warning messages
    """

    try:
        logging.disable(logging.WARNING)
        return conf.get(section, key)
    except AirflowConfigException:
        return default
    finally:
        logging.disable(logging.NOTSET)  # is guaranteed to be executed before any return


def collect_reports(
    context,
    task_ids=None
):
    """
    Collects reports from "context" for specified "task_ids".
    If "task_ids" was not set, use all tasks from DAG. Loads
    and merges data from reports.
    """

    task_ids = context["dag"].task_ids if task_ids is None else task_ids

    job_data = {}
    for report_location in context["ti"].xcom_pull(task_ids=task_ids):
        if report_location is not None:
            job_data = merge(
                job_data,
                load_yaml(report_location)
            )
    
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
            "inputs_folder": get_dir(                                             # for CWL-Airflow to resolve relative locations for input files if job was loaded from parsed object
                conf_get(
                    "cwl", "inputs_folder",
                    preset_cwl_args.get("inputs_folder", CWL_INPUTS_FOLDER)
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
                preset_cwl_args.get("use_container", CWL_USE_CONTAINER)            # execute jobs in docker containers
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
            "enable_dev": preset_cwl_args.get("enable_dev", CWL_ENABLE_DEV)        # fails to run without it when creating workflow from tool. TODO: Ask Peter?
        }
    )

    return required_cwl_args


def relocate_outputs(
    workflow,
    job_data,
    cwl_args=None,
    remove_tmp_folder=None
):
    """
    Relocates filtered outputs to "outputs_folder" and, by default,
    removes tmp_folder, unless "remove_tmp_folder" is set to something
    else. Saves report with relocated outputs as "workflow_report.json"
    to "outputs_folder".
    Maps outputs from "workflow" back to normal (from step_id_step_out
    to workflow output) and filters "job_data" based on them (combining
    items from "job_data" into a list based on "outputSource" if it
    was a list). "cwl_args" can be used to update default parameters
    used for loading and runtime contexts.
    """

    cwl_args = {} if cwl_args is None else cwl_args
    remove_tmp_folder = True if remove_tmp_folder is None else remove_tmp_folder

    default_cwl_args = get_default_cwl_args(cwl_args)

    workflow_tool = fast_cwl_load(
        workflow=workflow,
        cwl_args=default_cwl_args
    )

    # Filter "job_data" to include only items required by workflow outputs.
    # Remap keys to the proper workflow outputs IDs (without step id).
    # If "outputSource" was a list even of len=1, find all correspondent items
    # from the "job_data" and assign them as list of the same size. 
    job_data_copy = deepcopy(job_data)
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
    runtime_context = RuntimeContext(default_cwl_args)
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


def get_containers(job_data, task_id):
    """
    Searches for cidfiles in the "step_tmp_folder", loads
    container IDs from the found files, adds them to dict
    in a form of {cid: location}. If nothing found,
    returns {}.
    """

    containers = {}

    step_tmp_folder, _, _, _ = get_temp_folders(
        task_id=task_id,
        job_data=job_data
    )

    for location in get_files(step_tmp_folder, ".*\\.cid$").values():
        try:
            with open(location, "r") as input_stream:
                containers[input_stream.read()] = location
        except OSError as err:
            logging.error(f"Failed to read container ID \
                from {location} due to \n{err}")

    return containers


def kill_containers(containers):
    """
    Iterates over "containers" dictionary received from "get_containers"
    and tries to kill all running containers based on cid. If killed
    container was not in "running" state, was successfully killed or not
    found at all, removes correspondent cidfile.
    """

    docker_client = docker.from_env()
    for cid, location in containers.items():
        try:
            container = docker_client.containers.get(cid)
            if container.status == "running":
                container.kill()
            os.remove(location)
        except docker.errors.NotFound as err:
            os.remove(location)
        except docker.errors.APIError as err:
            logging.error(f"Failed to kill container. \n {err}")


def execute_workflow_step(
    workflow,
    task_id,
    job_data,
    cwl_args=None,
    executor=None
):
    """
    Constructs and executes single step workflow based on the "workflow"
    and "task_id". "cwl_args" can be used to update default parameters
    used for loading and runtime contexts. Exports json file with the
    execution results.
    """

    cwl_args = {} if cwl_args is None else cwl_args
    executor = SingleJobExecutor() if executor is None else executor

    step_tmp_folder, step_cache_folder, step_outputs_folder, step_report = get_temp_folders(
        task_id=task_id,
        job_data=job_data
    )

    default_cwl_args = get_default_cwl_args(cwl_args)

    default_cwl_args.update({                          # add execution specific parameters
        "tmp_outdir_prefix": step_cache_folder + "/",
        "tmpdir_prefix": step_cache_folder + "/",
        "cidfile_dir": step_tmp_folder,
        "cidfile_prefix": task_id,
        "basedir": os.getcwd(),                        # job should already have abs path for inputs, so this is useless
        "outdir": step_outputs_folder
    })
    
    workflow_step_path = os.path.join(
        step_tmp_folder, task_id + "_step_workflow.cwl"
    )

    fast_cwl_step_load(                                # will save new worlflow to "workflow_step_path"
        workflow=workflow,
        target_id=task_id,
        cwl_args=default_cwl_args,
        location=workflow_step_path
    )

    _stderr = sys.stderr                               # to trick the logger	
    sys.stderr = sys.__stderr__
    step_outputs, step_status = executor(
        slow_cwl_load(
            workflow=workflow_step_path,
            cwl_args=default_cwl_args),
        job_data,
        RuntimeContext(default_cwl_args)
    )
    sys.stderr = _stderr

    if step_status != "success":
        raise ValueError

    # To remove "http://commonwl.org/cwltool#generation": 0 (copied from cwltool)
    visit_class(step_outputs, ("File",), MutationManager().unset_generation)

    dump_json(step_outputs, step_report)

    return step_outputs, step_report


def get_temp_folders(task_id, job_data):
    """
    Creates a set of folders required for workflow execution.
    Uses "tmp_folder" from "job_data" as a parent folder.
    """

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


def load_job(
    workflow,
    job,
    cwl_args=None,
    cwd=None
):
    """
    Tries to load json object from "job". If failed, assumes that
    "job" has been already parsed into Object. Inits loaded "job_data"
    based on the "workflow" (mostly for setting defaults from the workflow
    inputs; never fails). "cwl_args" can be used to update parameters for
    loading and runtime contexts.

    If "job" was file, resolves relative paths based on the job file location.
    If "job" was already parsed into Object, resolves relative paths based on
    "cwd". If "cwd" was None uses "inputs_folder" value from "cwl_args" or
    its default value returned from "get_default_cwl_args" function.

    Checking links after relative paths are resolved is disabled (checklinks
    is set to False in both places). This will prevent rasing an exception by
    schema salad in those cases when an input file will be created from the
    provided content during workflow execution.
    
    Always returns CommentedMap
    """
    
    cwl_args = {} if cwl_args is None else cwl_args
    
    default_cwl_args = get_default_cwl_args(cwl_args)
    cwd = default_cwl_args["inputs_folder"] if cwd is None else cwd

    loading_context = setup_loadingContext(
        LoadingContext(default_cwl_args),
        RuntimeContext(default_cwl_args),
        argparse.Namespace(**default_cwl_args)
    )

    job_copy = deepcopy(job)

    try:
        job_data, _ = loading_context.loader.resolve_ref(job_copy, checklinks=False)
    except (FileNotFoundError, SchemaSaladException) as err:
        job_data = load_yaml(json.dumps(job_copy))
        job_data["id"] = file_uri(cwd) + "/"
        job_data, metadata = loading_context.loader.resolve_all(
            job_data,
            job_data["id"],
            checklinks=False
        )

    initialized_job_data = init_job_order(
        job_order_object=job_data,
        args=argparse.Namespace(**default_cwl_args),
        process=slow_cwl_load(
            workflow=workflow, 
            cwl_args=default_cwl_args
        ),
        loader=loading_context.loader,
        stdout=os.devnull
    )

    return initialized_job_data


def fast_cwl_step_load(workflow, target_id, cwl_args=None, location=None):
    """
    Returns workflow (CommentedMap) that includes only single step
    selected by "target_id" from the parsed "workflow". Other steps
    are removed. Workflow inputs and outputs are updated based on
    source fields of "in" and "out" from the selected workflow step.
    If selected step includes "scatter" field all output types will
    be transformed to the nested/flat array of items of the same type. 
    IDs of updated workflow inputs and outputs as well as IDs of
    correspondent "source" fields also include step id separated by
    underscore. All other fields remain unchanged.

    "cwl_args" can be used to update default location of "pickle_folder"
    used by "fast_cwl_load" as well as other parameters used by
    "slow_cwl_load" for loading and runtime contexts.

    If "location" is not None, export modified workflow.
    """

    cwl_args = {} if cwl_args is None else cwl_args

    default_cwl_args = get_default_cwl_args(cwl_args)

    workflow_inputs = []
    workflow_outputs = []
    workflow_steps = []

    workflow_tool = fast_cwl_load(
        workflow=workflow,
        cwl_args=default_cwl_args
    )

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

                # need to copy:
                #  original inputBinding because it can include loadContents section
                #  loadContents and loadListing sections if present outside of inputBinding
                #  both "default" and "secondaryFiles" if present
                # TODO: Do I need to copy format?
                for key in ["default", "secondaryFiles", "inputBinding", "loadContents", "loadListing"]:
                    if key in workflow_input:
                        updated_workflow_input[key] = workflow_input[key]

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

                upstream_step_tool = fast_cwl_load(
                    workflow=upstream_step["run"],
                    cwl_args=default_cwl_args
                )

                upstream_step_output = list(get_items(
                    {get_short_id(k, only_id=True): v for k, v in get_items(upstream_step_tool["outputs"])},  # trick
                    get_short_id(step_in_source, only_id=True)
                ))[0][1]

                step_in_source_with_step_id = step_in_source.replace("/", "_")  # to include both step name and id

                # Check if it should be assumed optional (default field is present)
                # NOTE: consider also checking if upstream step had scatter, so the
                # output type should become array based on the scatter parameters
                if "default" in step_in:
                    upstream_step_output_type = ["null", upstream_step_output["type"]]
                else:
                    upstream_step_output_type = upstream_step_output["type"]

                updated_workflow_input = {
                    "id": step_in_source_with_step_id,  
                    "type": upstream_step_output_type
                }

                # No need to copy "secondaryFiles" for outputs from other steps
                # because they should be already included into the generated json
                # report file
                # # TODO: Do I need to copy format to "workflow_inputs"?

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

    selected_step_tool = fast_cwl_load(
        workflow=selected_step["run"],
        cwl_args=default_cwl_args
    )

    for step_out, _ in get_items(selected_step["out"]):
        selected_step_output = list(get_items(
            {get_short_id(k, only_id=True): v for k, v in get_items(selected_step_tool["outputs"])},  # trick
            get_short_id(step_out, only_id=True)
        ))[0][1]
        step_out_with_step_id = step_out.replace("/", "_")  # to include both step name and id

        # update output type in case of scatter
        if "scatter" in selected_step:
            selected_step_output = deepcopy(selected_step_output)                  # need to deepcopy, otherwise we change embedded tool's output
            if isinstance(selected_step["scatter"], MutableSequence) \
                and selected_step.get("scatterMethod") == "nested_crossproduct":
                nesting = len(selected_step["scatter"])
            else:
                nesting = 1
            for _ in range(0, nesting):
                selected_step_output["type"] = {
                    "type": "array",
                    "items": selected_step_output["type"]
                }

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
    or more sections separated by "/", discard the middle ones.
    If part after symbol # includes only one section separated by
    "/", reset "only_step_name" and "only_id" to False as we don't
    know whether it was step name of "id"
    """
    fragment = urlsplit(long_id).fragment
    part = fragment if fragment != "" else long_id

    if len(part.split("/")) > 2:                                  # if "id" has weird stuff between step name and id
        part = "/".join([part.split("/")[0], part.split("/")[-1]])

    if len(part.split("/")) == 1:                                  # if fragment is only one word (based on "/")
        only_step_name, only_id = False, False

    part = part.split("/")[0] if only_step_name else part
    part = "/".join(part.split("/")[1:]) if only_id else part
    return part


def fast_cwl_load(workflow, cwl_args=None):
    """
    Tries to unpickle workflow from "pickle_folder" based on
    md5 sum of the "workflow" file. "cwl_args" can be used to update
    default location of "pickle_folder" as well as other parameters
    used by "slow_cwl_load" for loading and runtime contexts.
    
    If pickled file not found or failed to unpickle, load tool from
    the "workflow" using "slow_cwl_load" with "only_tool" set to True
    to return only tool. Returned tool will be pickled into "pickle_folder"
    with a basename generated from md5 sum of the "workflow" file.

    If "workflow" was already parsed into CommentedMap, return it unchanged.
    Nothing will be pickled
    """

    cwl_args = {} if cwl_args is None else cwl_args

    if isinstance(workflow, CommentedMap):
        return workflow

    default_cwl_args = get_default_cwl_args(cwl_args)

    pickled_workflow = os.path.join(
        default_cwl_args["pickle_folder"],
        get_md5_sum(workflow) + ".p"
    )

    try:

        with open(pickled_workflow, "rb") as input_stream:
            workflow_tool = pickle.load(input_stream)

    except (FileNotFoundError, pickle.UnpicklingError) as err:

        workflow_tool = slow_cwl_load(
            workflow=workflow,
            cwl_args=default_cwl_args,
            only_tool=True
        )

        with open(pickled_workflow , "wb") as output_stream:
            pickle.dump(workflow_tool, output_stream)

    return workflow_tool


def slow_cwl_load(workflow, cwl_args=None, only_tool=None):
    """
    Follows standard routine for loading CWL file the same way
    as cwltool does it. "workflow" should be an absolute path
    the cwl file to load. "cwl_args" can be used to update
    default arguments mostly used for loading and runtime contexts.
    If "only_tool" is True, return only tool (used for pickling,
    because the whole Workflow object later fails to be unpickled).
    If "workflow" was already parsed into CommentedMap, return it
    unchanged (in a form similar to what we can get if parsed
    "workflow" with "only_tool" set to True).
    If "workflow" was a zlib compressed content of a file, it needs
    to be uncompressed, then written to the temp file and loaded the
    same way as described above. After loading temp file will be
    removed automatically. First always try to uncompress, because
    it's faster.
    """
    
    cwl_args = {} if cwl_args is None else cwl_args
    only_tool = False if only_tool is None else only_tool

    if isinstance(workflow, CommentedMap):
        return workflow

    default_cwl_args = get_default_cwl_args(cwl_args)

    def __load(location):
        return load_tool(
            location,
            setup_loadingContext(
                LoadingContext(default_cwl_args),
                RuntimeContext(default_cwl_args),
                argparse.Namespace(**default_cwl_args)
            )
        )

    try:
        with NamedTemporaryFile(mode="w") as temp_stream:  # guarantees that temp file will be removed
            json.dump(
                get_uncompressed(workflow, parse_as_yaml=True),
                temp_stream
            )
            temp_stream.flush()                            # otherwise it might be only partially written
            workflow_data = __load(temp_stream.name)
    except (zlib.error, binascii.Error):                   # file was real
        workflow_data = __load(workflow)

    return workflow_data.tool if only_tool else workflow_data


def embed_all_runs(
    workflow_tool,
    cwl_args=None,
    location=None
):
    """
    Tries to find and load all "run" fields from the "workflow_tool"
    if it is Workflow. If not, doesn't replace anything. "cwl_args"
    can be used to update default arguments used by loading and runtime
    contexts. If "location" is provided, save resulted workflow to json
    file. Returns workflow tool with all "run" fields replaced.
    """

    def __embed(workflow_tool, cwl_args=None):
        if isinstance(workflow_tool, MutableSequence):
            for item in workflow_tool:
                __embed(item, cwl_args)
        elif isinstance(workflow_tool, MutableMapping):
            if "run" in workflow_tool and isinstance(workflow_tool["run"], str):
                workflow_tool["run"] = slow_cwl_load(
                    workflow=workflow_tool["run"],
                    cwl_args=cwl_args,
                    only_tool=True)
            for item in workflow_tool.values():
                __embed(item, cwl_args)

    if workflow_tool["class"] == "Workflow":
        workflow_tool_copy = deepcopy(workflow_tool)
        __embed(workflow_tool_copy, cwl_args)
    else:
        workflow_tool_copy = workflow_tool

    if location is not None:
        dump_json(workflow_tool_copy, location)

    return workflow_tool_copy


def convert_to_workflow(command_line_tool, location=None):
    """
    Converts "command_line_tool" to Workflow trying to keep all
    important elements. If "command_line_tool" is already Workflow,
    doesn't apply any changes. If "location" is not None, dumps
    results to json file.
    """

    if command_line_tool["class"] == "Workflow":
        workflow_tool = command_line_tool
    else:
        workflow_tool = {
            "class": "Workflow",
            "cwlVersion": command_line_tool["cwlVersion"],
            "inputs": [],
            "outputs": []
        }

        for key in ["requirements"]:
            if key in command_line_tool:
                workflow_tool[key] = command_line_tool[key]

        for input_id, input_data in get_items(command_line_tool["inputs"]):
            workflow_input = {
                "id": input_id,
                "type": remove_field_from_dict(input_data["type"], "inputBinding")       # "type" in WorkflowInputParameter cannot have "inputBinding"
            }
            for key in ["secondaryFiles", "default"]:  # TODO: Do I need to copy format?
                if key in input_data:
                    workflow_input[key] = input_data[key]
            workflow_tool["inputs"].append(workflow_input)

        for output_id, output_data in get_items(command_line_tool["outputs"]):
            workflow_output = {
                "id": output_id,
                "type": output_data["type"],
                "outputSource": get_rootname(command_line_tool["id"]) + "/" + output_id
            }
            # TODO: not sure if I need format here
            # for key in ["format"]:
            #     if key in output_data:
            #         workflow_output[key] = output_data[key]
            workflow_tool["outputs"].append(workflow_output)

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
