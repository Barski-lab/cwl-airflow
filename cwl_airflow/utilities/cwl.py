import os
import sys
import dill as pickle  # standard pickle doesn't handle lambdas
import argparse
import json
import errno
import shutil

from uuid import uuid4
from copy import deepcopy
from tempfile import mkdtemp
from urllib.parse import urlsplit
from typing import Mapping, Sequence
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from cwltool.main import setup_loadingContext, init_job_order
from cwltool.context import LoadingContext, RuntimeContext
from cwltool.process import relocateOutputs
from cwltool.load_tool import load_tool, jobloaderctx
from cwltool.executors import SingleJobExecutor
from schema_salad.ref_resolver import Loader
from schema_salad.exceptions import SchemaSaladException
from schema_salad.ref_resolver import file_uri

from cwl_airflow.utilities.helpers import (
    get_md5_sum,
    get_dir,
    get_path_from_url
)


def relocate_outputs(cwl_args, job_data, remove_tmp_folder=None):
    """
    Maps outputs back to normal,
    By default remove tmp_folder, unless "remove_tmp_folder" is set
    to False
    """
    
    remove_tmp_folder = True if remove_tmp_folder is None else remove_tmp_folder

    cwl_args_copy = deepcopy(cwl_args)
    job_data_copy = deepcopy(job_data)

    workflow_tool = fast_cwl_load(cwl_args_copy)

    # get outputs mapping
    mapped_outputs = {}
    for output_id, output_data in get_items(workflow_tool["outputs"]):
        for output_source_id, _ in get_items(output_data["outputSource"]):
            output_source_id_with_step_id = output_source_id.replace("/", "_")
            mapped_outputs[output_source_id_with_step_id] = output_id

    # filter job_data_copy to include only items from "mapped_outputs"
    filtered_job_data = {}
    for output_id, output_data in get_items(job_data_copy):
        if output_id in mapped_outputs:
            filtered_job_data[mapped_outputs[output_id]] = output_data

    runtime_context = RuntimeContext(cwl_args_copy)

    relocated_job_data = relocateOutputs(
        outputObj=filtered_job_data,
        destination_path=job_data_copy["outputs_folder"],
        source_directories=[],
        action=runtime_context.move_outputs,
        fs_access=runtime_context.make_fs_access(""),
        compute_checksum=runtime_context.compute_checksum,
        path_mapper=runtime_context.path_mapper
    )

    workflow_report = os.path.join(
        job_data_copy["outputs_folder"],
        "workflow_report.json"
    )

    dump_data(relocated_job_data, workflow_report)

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

    dump_data(step_outputs, step_report)

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


def dump_data(data, location):
    with open(location , "w") as output_stream:
        json.dump(data, output_stream, indent=4)


def load_job(cwl_args, job, cwd=None):
    """
    Follows standard routine for loading job order object file
    the same way as cwltool does it. cwl_args should include
    "workflow" field.
    
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

    cwl_args_copy = deepcopy(cwl_args)
    job_copy = deepcopy(job)

    loading_context = setup_loadingContext(
        LoadingContext(cwl_args_copy),
        RuntimeContext(cwl_args_copy),
        argparse.Namespace(**cwl_args_copy)
    )

    try:
        job_data, _ = loading_context.loader.resolve_ref(job_copy, checklinks=True)
    except (FileNotFoundError, SchemaSaladException) as err:
        yaml = YAML()
        yaml.preserve_quotes = True
        job_data = yaml.load(json.dumps(job_copy))
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
                workflow_inputs.append({
                    "id": step_in_source_with_step_id,  
                    "type": upstream_step_output["type"]
                })
                
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
        dump_data(workflow_tool, location)

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

    if isinstance(data, Mapping):
        for key, value in data.items():
            if target_id is not None:
                if key == target_id or get_short_id(key) == target_id:
                    yield get_short_id(key), value 
                else:
                    continue
            else:
                yield get_short_id(key), value 
    elif isinstance(data, Sequence) and not isinstance(data, str):
        for item in data:
            if "id" in item:
                if target_id is not None:
                    if item["id"] == target_id or get_short_id(item["id"]) == target_id:
                        yield get_short_id(item["id"]), item
                    else:
                        continue
                else:
                    yield get_short_id(item["id"]), item
            elif isinstance(item, str):
                if target_id is not None:
                    if item == target_id or get_short_id(item) == target_id:
                        yield get_short_id(item), item
                    else:
                        continue
                else:
                    yield get_short_id(item), item
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
