import os
import dill as pickle  # standard pickle doesn't handle lambdas
import argparse

from urllib.parse import urlsplit
from typing import Mapping, Sequence
from cwltool.main import setup_loadingContext
from cwltool.context import LoadingContext, RuntimeContext
from cwltool.load_tool import load_tool

from cwl_airflow.utilities.helpers import get_md5_sum


def get_items(data):
    """
    If data is dictionary returns [(key, value)].
    
    If data is string return [key].
    
    If data is list of items returns [(key, value)] with key set
    from item["id"] and value equal to the item itlself. If item
    was string, set key from this string and return [keys].
    
    For all other cases return either list of unchanged items or
    unchanged input data.
    
    Keys are always shortened to include only part after symbol #
    """
    if isinstance(data, Mapping):
        for key, value in data.items():
            yield get_short_id(key), value 
    elif isinstance(data, Sequence) and not isinstance(data, str):
        for item in data:
            if "id" in item:
                yield get_short_id(item["id"]), item
            elif isinstance(item, str):
                yield get_short_id(item)
            else:
                yield item
    elif isinstance(data, str):
        yield get_short_id(data)
    else:
        yield data


def get_short_id(long_id):
    """
    Shortens long id to include only part after symbol #
    """
    return urlsplit(long_id).fragment


def fast_cwl_load(default_args):
    """
    Pass default_args despite the fact that only cwl section
    is required. Just to make it easier to call this function.

    Tries to load pickled version of CWL file from the
    pickle_folder. Uses md5 sum as a basename for the file.
    If file not found or failed to unpickle, load CWL data
    from the workflow file and save pickled version.

    default_args["cwl"] should include "pickle_folder" and
    "workflow". Other args are required for a proper LoadingContext
    and RuntimeContext construction when calling slow_cwl_load.

    Returned value is always CommentedMap which includes parsed tool.
    slow_cwl_load is always called with reduced=True. Dill will fails
    to pickle/unpickle the whole workflow
    """

    cwl_args = default_args["cwl"]  # for easier access

    pickled_workflow = os.path.join(
        cwl_args["pickle_folder"],
        get_md5_sum(cwl_args["workflow"]) + ".p"
    )

    try:
        with open(pickled_workflow, "rb") as input_stream:
            workflow_data = pickle.load(input_stream)
    except (FileNotFoundError, pickle.UnpicklingError) as err:
        workflow_data = slow_cwl_load(cwl_args, True)
        with open(pickled_workflow , "wb") as output_stream:
            pickle.dump(workflow_data, output_stream)

    return workflow_data


def slow_cwl_load(cwl_args, reduced=False):
    """
    Follows standard routine for loading CWL file.
    The same way as cwltool does it. If 'reduced' is
    True, return only tool (useful for pickling,
    because the whole Workflow object fails to be
    unpickled)
    """

    workflow_data = load_tool(
        cwl_args["workflow"], 
        setup_loadingContext(
            LoadingContext(cwl_args),
            RuntimeContext(cwl_args),
            argparse.Namespace(**cwl_args)
        )
    )

    return workflow_data.tool if reduced else workflow_data
