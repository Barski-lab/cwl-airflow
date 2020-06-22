import os
import dill as pickle  # standard pickle doesn't handle lambdas
import argparse
import json
import errno

from copy import deepcopy
from tempfile import mkdtemp
from urllib.parse import urlsplit
from typing import Mapping, Sequence
from ruamel.yaml import YAML
from cwltool.main import setup_loadingContext, init_job_order
from cwltool.context import LoadingContext, RuntimeContext
from cwltool.load_tool import load_tool, jobloaderctx
from cwltool.executors import SingleJobExecutor
from schema_salad.ref_resolver import Loader
from schema_salad.exceptions import SchemaSaladException
from schema_salad.ref_resolver import file_uri

from cwl_airflow.utilities.helpers import get_md5_sum


def execute(worfklow_tool, job, default_args, executor=None):

    default_args_copy = deepcopy(default_args)
    cwl_args = default_args_copy["cwl"]         # for easy access

    executor = SingleJobExecutor() if executor is None else executor

    runtime_context = RuntimeContext(cwl_args)

    step_tmp = tempfile.mkdtemp(
        prefix=os.path.join(cwl_args["tmp_folder"], "step_")
    )

    runtime_context.tmp_outdir_prefix = os.path.join(cwl_args["tmp_folder"], "outdir_")
    runtime_context.tmpdir_prefix = os.path.join(cwl_args["tmp_folder"], "tmpdir_")
    runtime_context.cachedir = os.path.join(cwl_args["tmp_folder"], "cachedir_")

    runtime_context.rm_tmpdir = True
    runtime_context.cidfile_dir
    runtime_context.cidfile_prefix

    runtime_context.move_outputs = "move"
    runtime_context.basedir = os.getcwd()  # job should have abs path for inputs, so this is useless
    
    runtime_context.outdir = ""

    step_outputs, step_status = executor(workflow_step_tool, job, runtime_context)


def load_job(job, cwl_args, cwd=None):
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


def fast_cwl_step_load(default_args, target_id):
    """
    Pass default_args despite the fact that only "cwl" section
    is required. Just to make it easier to call this function.
    
    default_args["cwl"] should include "pickle_folder" and
    "workflow". Other args are required for a proper LoadingContext
    and RuntimeContext construction when calling fast_cwl_load.

    Constructs workflow from a single step selected by its id.
    Other steps are removed. Workflow inputs and outputs are
    updated based on source fields of "in" and "out" from the
    selected workflow step. All other fields remain unchanged.

    Returned value is always CommentedMap with parsed tool.
    """

    default_args_copy = deepcopy(default_args)

    workflow_inputs = []
    workflow_outputs = []
    workflow_steps = []

    workflow_tool = fast_cwl_load(default_args_copy)

    selected_step = list(get_items(workflow_tool["steps"], target_id))[0][1]

    workflow_steps.append(selected_step)

    for _, step_in in get_items(selected_step.get("in", [])):           # step might not have "in"
        for _, step_in_source in get_items(step_in.get("source", [])):  # "in" might not have "source"
            
            try:

                # try to find workflow input that corresponds to "source"

                workflow_input = list(get_items(
                    workflow_tool["inputs"],
                    step_in_source
                ))[0][1]
                workflow_inputs.append(workflow_input)

            except (IndexError, KeyError):
                
                # Need to find upstream step that corresponds to "source"

                upstream_step = list(get_items(
                    workflow_tool["steps"],
                    get_short_id(step_in_source, only_step_name=True)
                ))[0][1]

                # Need to load tool from "run" of the found upstream step
                # and look for the output that corresponds to "source"

                default_args_copy["cwl"]["workflow"] = upstream_step["run"]
                upstream_step_tool = fast_cwl_load(default_args_copy)

                upstream_step_output = list(get_items(
                    upstream_step_tool["outputs"],
                    get_short_id(step_in_source, only_id=True)
                ))[0][1]

                workflow_inputs.append({
                    "id": step_in_source,
                    "type": upstream_step_output["type"]  # TODO: maybe I need to copy format too
                })

    # Need to load tool from the "run" field of the selected step
    # and look for the outputs that correpond to the items from "out"

    default_args_copy["cwl"]["workflow"] = selected_step["run"]
    selected_step_tool = fast_cwl_load(default_args_copy)

    for _, step_out in get_items(selected_step["out"]):
        selected_step_output = list(get_items(
            selected_step_tool["outputs"],
            get_short_id(step_out, only_id=True)
        ))[0][1]
        workflow_outputs.append({
            "id": step_out,                         # looks like it's safe to set both "id" and "outputSource" with the same name
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
    If only_step_name is True, return a short step name.
    If only_id is True, return a short id without step name.
    """
    part = urlsplit(long_id).fragment
    part = part.split("/")[0] if only_step_name else part
    part = "/".join(part.split("/")[1:]) if only_id else part
    return part


def fast_cwl_load(default_args):
    """
    Pass default_args despite the fact that only "cwl" section
    is required. Just to make it easier to call this function.
    "cwl" section should include "workflow" and "pickle_folder"
    fields.

    Tries to load pickled version of CWL file from the
    pickle_folder. Uses md5 sum as a basename for the file.
    If file not found or failed to unpickle, load CWL data
    from the workflow file and save pickled version.

    default_args["cwl"] should include "pickle_folder" and
    "workflow". Other args are required for a proper LoadingContext
    and RuntimeContext construction when calling slow_cwl_load.

    Returned value is always CommentedMap with parsed tool, because
    slow_cwl_load is always called with reduced=True. Dill will fail
    to pickle/unpickle the whole workflow
    """

    cwl_args = default_args["cwl"]  # for easier access

    pickled_workflow = os.path.join(
        cwl_args["pickle_folder"],
        get_md5_sum(cwl_args["workflow"]) + ".p"
    )

    try:
        with open(pickled_workflow, "rb") as input_stream:
            workflow_tool = pickle.load(input_stream)
    except (FileNotFoundError, pickle.UnpicklingError) as err:
        workflow_tool = slow_cwl_load(cwl_args, True)
        with open(pickled_workflow , "wb") as output_stream:
            pickle.dump(workflow_tool, output_stream)

    return workflow_tool


def slow_cwl_load(cwl_args, reduced=False):
    """
    Follows standard routine for loading CWL file
    the same way as cwltool does it. cwl_args should
    include "workflow" field. If 'reduced' is
    True, return only tool (useful for pickling,
    because the whole Workflow object fails to be
    unpickled)
    """

    if not os.path.isfile(cwl_args["workflow"]):
        raise FileNotFoundError(
            errno.ENOENT, os.strerror(errno.ENOENT), cwl_args["workflow"]
        )

    workflow_data = load_tool(
        cwl_args["workflow"], 
        setup_loadingContext(
            LoadingContext(cwl_args),
            RuntimeContext(cwl_args),
            argparse.Namespace(**cwl_args)
        )
    )

    return workflow_data.tool if reduced else workflow_data
