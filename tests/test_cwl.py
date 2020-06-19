import os
import copy
import pytest

from shutil import rmtree, copy
from tempfile import mkdtemp
from ruamel.yaml.comments import CommentedMap
from cwltool.argparser import get_default_args
from cwltool.workflow import Workflow

from cwl_airflow.utilities.helpers import get_md5_sum
from cwl_airflow.utilities.cwl import (
    fast_cwl_load,
    slow_cwl_load,
    get_items
)


DATA_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))


def test_slow_cwl_load():
    cwl_args = get_default_args()
    cwl_args.update(
        {
            "workflow": os.path.join(
                DATA_FOLDER, "workflows", "bam-bedgraph-bigwig.cwl"
            ) 
        }
    )
    workflow_data = slow_cwl_load(cwl_args)

    assert isinstance(workflow_data, Workflow)


def test_slow_cwl_load_reduced():
    cwl_args = get_default_args()
    cwl_args.update(
        {
            "workflow": os.path.join(
                DATA_FOLDER, "workflows", "bam-bedgraph-bigwig.cwl"
            ) 
        }
    )
    workflow_data = slow_cwl_load(cwl_args, True)

    assert isinstance(workflow_data, CommentedMap)


def test_fast_cwl_load_from_cwl():
    temp_pickle_folder = mkdtemp()
    workflow = os.path.join(DATA_FOLDER, "workflows", "bam-bedgraph-bigwig.cwl")
    pickled_workflow = get_md5_sum(workflow) + ".p"

    cwl_args = get_default_args()
    cwl_args.update(
        {
            "workflow": workflow,
            "pickle_folder": temp_pickle_folder
        }
    )
    try:
        workflow_data = fast_cwl_load({"cwl": cwl_args})
        temp_pickle_folder_content = os.listdir(temp_pickle_folder)
    except BaseException as err:
        assert False, f"Failed to run test. \n {err}"
    finally:
        rmtree(temp_pickle_folder)

    assert isinstance(workflow_data, CommentedMap), \
           "Failed to parse CWL file"
    assert pickled_workflow in temp_pickle_folder_content, \
           "Failed to pickle CWL file"
    

def test_fast_cwl_load_from_pickle():
    temp_pickle_folder = mkdtemp()
    original_workflow = os.path.join(
        DATA_FOLDER, "workflows", "bam-bedgraph-bigwig.cwl"
    )
    duplicate_workflow = os.path.join(
        temp_pickle_folder, "bam-bedgraph-bigwig.cwl"       # will fail if parsed directly
    )
    copy(original_workflow, duplicate_workflow)
    
    cwl_args = get_default_args()
    cwl_args.update(
        {
            "workflow": original_workflow,
            "pickle_folder": temp_pickle_folder
        }
    )
    try:
        workflow_data = fast_cwl_load({"cwl": cwl_args})         # should result in creating pickled file
        cwl_args["workflow"] = duplicate_workflow
        workflow_data = fast_cwl_load({"cwl": cwl_args})         # should load from pickled file
    except BaseException as err:
        assert False, f"Failed to run test. \n {err}"
    finally:
        rmtree(temp_pickle_folder)

    assert isinstance(workflow_data, CommentedMap), \
           "Failed to load pickled CWL file"


@pytest.mark.parametrize(
    "inputs, controls",
    [
        (
            [
                {
                    "type": "File",
                    "doc": "Input BAM file, sorted by coordinates",
                    "id": "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#bam_file"
                },
                {
                    "type": ["null", "string"],
                    "doc": "Output filename for generated bedGraph",
                    "id": "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#bedgraph_filename"
                },
                {
                    "type": ["null", "string"],
                    "doc": "Output filename for generated bigWig",
                    "id": "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#bigwig_filename"
                }
            ],
            [
                (
                    "bam_file",
                    {
                        "type": "File",
                        "doc": "Input BAM file, sorted by coordinates",
                        "id": "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#bam_file"
                    }
                ),
                (
                    "bedgraph_filename",
                    {
                        "type": ["null", "string"],
                        "doc": "Output filename for generated bedGraph",
                        "id": "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#bedgraph_filename"
                    }
                ),
                (   "bigwig_filename",
                    {
                        "type": ["null", "string"],
                        "doc": "Output filename for generated bigWig",
                        "id": "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#bigwig_filename"
                    }
                )
            ]
        ),
        (
            [
                "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sorted_bedgraph_to_bigwig/bigwig_file",
                "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sort_bedgraph/sorted_file"
            ],
            ["sorted_bedgraph_to_bigwig/bigwig_file", "sort_bedgraph/sorted_file"]
        ),
        (
            {
                "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#bam_file": {
                    "type": "File",
                    "doc": "Input BAM file, sorted by coordinates",
                },
                "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#bedgraph_filename": {
                    "type": ["null", "string"],
                    "doc": "Output filename for generated bedGraph",
                }
            },
            [
                (
                    "bam_file",
                    {
                        "type": "File",
                        "doc": "Input BAM file, sorted by coordinates"
                    }
                ),
                (
                    "bedgraph_filename",
                    {
                        "type": ["null", "string"],
                        "doc": "Output filename for generated bedGraph"
                    }
                )
            ]
        ),
        (
            [
                [
                    "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sorted_bedgraph_to_bigwig/bigwig_file",
                    "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sort_bedgraph/sorted_file"
                ]
            ],
            [
                [
                    "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sorted_bedgraph_to_bigwig/bigwig_file",
                    "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sort_bedgraph/sorted_file"
                ]
            ]
        ),
        (
            10,
            [10]
        ),
        (
            "file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bigwig_filename",
            ["bigwig_filename"]
        ),
        (
            [],
            []
        )
    ]
)
def test_get_items(inputs, controls):
    results = list(get_items(inputs))
    assert results == controls
