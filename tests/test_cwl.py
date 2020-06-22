import os
import sys
import copy
import pytest

from shutil import rmtree, copy
from tempfile import mkdtemp
from ruamel.yaml.comments import CommentedMap
from cwltool.argparser import get_default_args
from cwltool.workflow import Workflow
from cwltool.command_line_tool import CommandLineTool

from cwl_airflow.utilities.helpers import get_md5_sum, get_absolute_path
from cwl_airflow.utilities.cwl import (
    fast_cwl_load,
    slow_cwl_load,
    fast_cwl_step_load,
    load_job,
    get_items
)


DATA_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))


# @pytest.mark.parametrize(
#     "target_id, control_workflow",
#     [
#         (
#             "bam_to_bedgraph",
#             "bam-to-bedgraph-step.cwl"
#         ),
#         (
#             "sort_bedgraph",
#             "sort-bedgraph-step.cwl"
#         ),
#         (
#             "sorted_bedgraph_to_bigwig",
#             "sorted-bedgraph-to-bigwig-step.cwl"
#         )
#     ]
# )
# def test_fast_cwl_step_load(target_id, control_workflow):
#     temp_pickle_folder = mkdtemp()
#     workflow_path = os.path.join(DATA_FOLDER, "workflows", "bam-bedgraph-bigwig.cwl")
#     control_workflow_path = os.path.join(DATA_FOLDER, "controls", control_workflow)

#     cwl_args = get_default_args()
#     cwl_args.update(
#         {
#             "workflow": workflow_path,
#             "pickle_folder": temp_pickle_folder
#         }
#     )
#     try:
#         workflow_step_tool = fast_cwl_step_load({"cwl": cwl_args}, target_id)
#         cwl_args["workflow"] = control_workflow_path
#         control_workflow_step_tool = fast_cwl_load({"cwl": cwl_args})
#     except BaseException as err:
#         assert False, f"Failed to run test. \n {err}"
#     finally:
#         rmtree(temp_pickle_folder)

#     assert workflow_step_tool == control_workflow_step_tool, \
#            "Failed to build workflow from the selected step"


@pytest.mark.parametrize(
    "job, workflow",
    [
        (
            "bam-bedgraph-bigwig-1.json",
            ["workflows", "bam-bedgraph-bigwig.cwl"]
        )
    ]
)
def test_load_job_from_file(job, workflow):
    temp_pickle_folder = mkdtemp()
    workflow_path = os.path.join(DATA_FOLDER, *workflow)
    job_path = os.path.join(DATA_FOLDER, "jobs", job)

    cwl_args = get_default_args()
    cwl_args.update(
        {
            "workflow": workflow_path,
            "pickle_folder": temp_pickle_folder
        }
    )
    try:
        job_data = load_job(job_path, cwl_args)
    except BaseException as err:
        assert False, f"Failed to load job from file"
    finally:
        rmtree(temp_pickle_folder)


@pytest.mark.parametrize(
    "job, workflow",
    [
        (
            "bam-bedgraph-bigwig-1.json",
            ["workflows", "dummy.cwl"]
        )
    ]
)
def test_load_job_from_file_should_fail(job, workflow):
    with pytest.raises(AssertionError):
        test_load_job_from_file(job, workflow)


@pytest.mark.parametrize(
    "job, workflow, cwd",
    [
        (
            {
                "bam_file": {
                    "class": "File",
                    "location": "../inputs/chr4_100_mapped_reads.bam"
                },
                "chrom_length_file": {
                    "class": "File",
                    "location": "../inputs/chr_name_length.txt"
                },
                "scale": 1
            },
            ["workflows", "bam-bedgraph-bigwig.cwl"],
            os.path.join(DATA_FOLDER, "jobs")
        ),
        (
            {
                "bam_file": {
                    "class": "File",
                    "location": get_absolute_path(
                        "../inputs/chr4_100_mapped_reads.bam",
                        os.path.join(DATA_FOLDER, "jobs")
                    )
                },
                "chrom_length_file": {
                    "class": "File",
                    "location": get_absolute_path(
                        "../inputs/chr_name_length.txt",
                        os.path.join(DATA_FOLDER, "jobs")
                    )
                },
                "scale": 1
            },
            ["workflows", "bam-bedgraph-bigwig.cwl"],
            os.path.join(DATA_FOLDER, "jobs")
        ),
        (
            {
                "bam_file": {
                    "class": "File",
                    "location": "../inputs/chr4_100_mapped_reads.bam"
                },
                "chrom_length_file": {
                    "class": "File",
                    "location": "../inputs/chr_name_length.txt"
                },
                "scale": 1
            },
            ["workflows", "bam-bedgraph-bigwig.cwl"],
            None
        ),
        (
            {
                "bam_file": {
                    "class": "File",
                    "location": get_absolute_path(
                        "../inputs/chr4_100_mapped_reads.bam",
                        os.path.join(DATA_FOLDER, "jobs")
                    )
                },
                "chrom_length_file": {
                    "class": "File",
                    "location": get_absolute_path(
                        "../inputs/chr_name_length.txt",
                        os.path.join(DATA_FOLDER, "jobs")
                    )
                },
                "scale": 1
            },
            ["workflows", "bam-bedgraph-bigwig.cwl"],
            None
        ),
        (
            {
                "bam_file": {
                    "class": "File",
                    "location": "../inputs/dummy.txt"
                },
                "chrom_length_file": {
                    "class": "File",
                    "location": "../inputs/dummy.txt"
                },
                "scale": 1
            },
            ["workflows", "bam-bedgraph-bigwig.cwl"],
            None
        ),
        (
            {
                "bam_file": {
                    "class": "File",
                    "location": get_absolute_path(
                        "../inputs/dummy.txt",
                        os.path.join(DATA_FOLDER, "jobs")
                    )
                },
                "chrom_length_file": {
                    "class": "File",
                    "location": get_absolute_path(
                        "../inputs/dummy.txt",
                        os.path.join(DATA_FOLDER, "jobs")
                    )
                },
                "scale": 1
            },
            ["workflows", "bam-bedgraph-bigwig.cwl"],
            None
        )
    ]
)
def test_load_job_from_object(job, workflow, cwd):
    temp_pickle_folder = mkdtemp()
    workflow_path = os.path.join(DATA_FOLDER, *workflow)
    
    cwl_args = get_default_args()
    cwl_args.update(
        {
            "workflow": workflow_path,
            "pickle_folder": temp_pickle_folder
        }
    )
    try:
        job_data = load_job(job, cwl_args, cwd)
    except BaseException as err:
        assert False, f"Failed to load job from parsed object"
    finally:
        rmtree(temp_pickle_folder)


@pytest.mark.parametrize(
    "job, workflow, cwd",
    [
        (
            {
                "bam_file": {
                    "class": "File",
                    "location": "../inputs/dummy.txt"
                },
                "chrom_length_file": {
                    "class": "File",
                    "location": "../inputs/dummy.txt"
                },
                "scale": 1
            },
            ["workflows", "bam-bedgraph-bigwig.cwl"],
            os.path.join(DATA_FOLDER, "jobs")
        ),
        (
            {
                "bam_file": {
                    "class": "File",
                    "location": get_absolute_path(
                        "../inputs/dummy.txt",
                        os.path.join(DATA_FOLDER, "jobs")
                    )
                },
                "chrom_length_file": {
                    "class": "File",
                    "location": get_absolute_path(
                        "../inputs/dummy.txt",
                        os.path.join(DATA_FOLDER, "jobs")
                    )
                },
                "scale": 1
            },
            ["workflows", "bam-bedgraph-bigwig.cwl"],
            os.path.join(DATA_FOLDER, "jobs")
        ),
        (
            {
                "bam_file": {
                    "class": "File",
                    "location": "../inputs/dummy.txt"
                },
                "chrom_length_file": {
                    "class": "File",
                    "location": "../inputs/dummy.txt"
                },
                "scale": 1
            },
            ["workflows", "dummy.cwl"],
            None
        )
    ]
)
def test_load_job_from_object_should_fail(job, workflow, cwd):
    with pytest.raises(AssertionError):
        test_load_job_from_object(job, workflow, cwd)


def test_slow_cwl_load_workflow():
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


def test_slow_cwl_load_command_line_tool():
    cwl_args = get_default_args()
    cwl_args.update(
        {
            "workflow": os.path.join(
                DATA_FOLDER, "tools", "linux-sort.cwl"
            ) 
        }
    )
    command_line_tool_data = slow_cwl_load(cwl_args)

    assert isinstance(command_line_tool_data, CommandLineTool)


def test_slow_cwl_load_reduced_workflow():
    cwl_args = get_default_args()
    cwl_args.update(
        {
            "workflow": os.path.join(
                DATA_FOLDER, "workflows", "bam-bedgraph-bigwig.cwl"
            ) 
        }
    )
    workflow_tool = slow_cwl_load(cwl_args, True)

    assert isinstance(workflow_tool, CommentedMap)


def test_slow_cwl_load_reduced_command_line_tool():
    cwl_args = get_default_args()
    cwl_args.update(
        {
            "workflow": os.path.join(
                DATA_FOLDER, "tools", "linux-sort.cwl"
            ) 
        }
    )
    command_line_tool = slow_cwl_load(cwl_args, True)

    assert isinstance(command_line_tool, CommentedMap)


def test_slow_cwl_load_workflow_should_fail():
    cwl_args = get_default_args()
    cwl_args.update(
        {
            "workflow": os.path.join(
                DATA_FOLDER, "workflows", "dummy.cwl"
            ) 
        }
    )
    with pytest.raises(FileNotFoundError):
        workflow_data = slow_cwl_load(cwl_args)
    

def test_fast_cwl_load_workflow_from_cwl():
    temp_pickle_folder = mkdtemp()
    workflow_path = os.path.join(DATA_FOLDER, "workflows", "bam-bedgraph-bigwig.cwl")
    pickled_workflow_path = get_md5_sum(workflow_path) + ".p"

    cwl_args = get_default_args()
    cwl_args.update(
        {
            "workflow": workflow_path,
            "pickle_folder": temp_pickle_folder
        }
    )
    try:
        workflow_tool = fast_cwl_load({"cwl": cwl_args})
        temp_pickle_folder_content = os.listdir(temp_pickle_folder)
    except BaseException as err:
        assert False, f"Failed to run test. \n {err}"
    finally:
        rmtree(temp_pickle_folder)

    assert isinstance(workflow_tool, CommentedMap), \
           "Failed to parse CWL file"
    assert pickled_workflow_path in temp_pickle_folder_content, \
           "Failed to pickle CWL file"
    

def test_fast_cwl_load_command_line_tool_from_cwl():
    temp_pickle_folder = mkdtemp()
    command_line_tool_path = os.path.join(DATA_FOLDER, "tools", "linux-sort.cwl")
    pickled_command_line_tool_path = get_md5_sum(command_line_tool_path) + ".p"

    cwl_args = get_default_args()
    cwl_args.update(
        {
            "workflow": command_line_tool_path,
            "pickle_folder": temp_pickle_folder
        }
    )
    try:
        command_line_tool = fast_cwl_load({"cwl": cwl_args})
        temp_pickle_folder_content = os.listdir(temp_pickle_folder)
    except BaseException as err:
        assert False, f"Failed to run test. \n {err}"
    finally:
        rmtree(temp_pickle_folder)

    assert isinstance(command_line_tool, CommentedMap), \
           "Failed to parse CWL file"
    assert pickled_command_line_tool_path in temp_pickle_folder_content, \
           "Failed to pickle CWL file"


def test_fast_cwl_load_workflow_from_pickle():
    temp_pickle_folder = mkdtemp()
    original_workflow_path = os.path.join(
        DATA_FOLDER, "workflows", "bam-bedgraph-bigwig.cwl"
    )
    duplicate_workflow_path = os.path.join(
        temp_pickle_folder, "bam-bedgraph-bigwig.cwl"       # will fail if parsed directly
    )
    copy(original_workflow_path, duplicate_workflow_path)
    
    cwl_args = get_default_args()
    cwl_args.update(
        {
            "workflow": original_workflow_path,
            "pickle_folder": temp_pickle_folder
        }
    )
    try:
        workflow_tool = fast_cwl_load({"cwl": cwl_args})         # should result in creating pickled file
        cwl_args["workflow"] = duplicate_workflow_path
        workflow_tool = fast_cwl_load({"cwl": cwl_args})         # should load from pickled file
    except BaseException as err:
        assert False, f"Failed to run test. \n {err}"
    finally:
        rmtree(temp_pickle_folder)

    assert isinstance(workflow_tool, CommentedMap), \
           "Failed to load pickled CWL file"


def test_fast_cwl_load_command_line_tool_from_pickle():
    temp_pickle_folder = mkdtemp()
    original_command_line_tool_path = os.path.join(
        DATA_FOLDER, "tools", "linux-sort.cwl"
    )
    duplicate_command_line_tool_path = os.path.join(
        temp_pickle_folder, "linux-sort.cwl"
    )
    copy(original_command_line_tool_path, duplicate_command_line_tool_path)
    
    cwl_args = get_default_args()
    cwl_args.update(
        {
            "workflow": original_command_line_tool_path,
            "pickle_folder": temp_pickle_folder
        }
    )
    try:
        command_line_tool = fast_cwl_load({"cwl": cwl_args})  # should result in creating pickled file
        cwl_args["workflow"] = duplicate_command_line_tool_path
        command_line_tool = fast_cwl_load({"cwl": cwl_args})  # should load from pickled file
    except BaseException as err:
        assert False, f"Failed to run test. \n {err}"
    finally:
        rmtree(temp_pickle_folder)

    assert isinstance(command_line_tool, CommentedMap), \
           "Failed to load pickled CWL file"


def test_fast_cwl_load_workflow_from_cwl_should_fail():
    temp_pickle_folder = mkdtemp()
    workflow_path = os.path.join(DATA_FOLDER, "workflows", "dummy.cwl")

    cwl_args = get_default_args()
    cwl_args.update(
        {
            "workflow": workflow_path,
            "pickle_folder": temp_pickle_folder
        }
    )
    with pytest.raises(AssertionError):
        try:
            workflow_tool = fast_cwl_load({"cwl": cwl_args})
        except BaseException as err:
            assert False, f"Should raise because cwl wasn't found. \n {err}"
        finally:
            rmtree(temp_pickle_folder)


@pytest.mark.parametrize(
    "inputs, target_id, controls",
    [
        # when target_id is not set
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
            None,
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
            None,
            [
                (
                    "sorted_bedgraph_to_bigwig/bigwig_file",
                    "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sorted_bedgraph_to_bigwig/bigwig_file"
                ), 
                (
                    "sort_bedgraph/sorted_file",
                    "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sort_bedgraph/sorted_file"
                )
            ]
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
            None,
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
            None,
            [
                (
                    [
                        "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sorted_bedgraph_to_bigwig/bigwig_file",
                        "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sort_bedgraph/sorted_file"
                    ],
                    [
                        "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sorted_bedgraph_to_bigwig/bigwig_file",
                        "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sort_bedgraph/sorted_file"
                    ]
                )
            ]
        ),
        (
            10,
            None,
            [(10, 10)]
        ),
        (
            "file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bigwig_filename",
            None,
            [
                (
                    "bigwig_filename",
                    "file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bigwig_filename"
                )
            ]
        ),
        (
            [],
            None,
            []
        ),
        # when target_id is set
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
            "bam_file",
            [
                (
                    "bam_file",
                    {
                        "type": "File",
                        "doc": "Input BAM file, sorted by coordinates",
                        "id": "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#bam_file"
                    }
                )
            ]
        ),
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
            "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#bam_file",
            [
                (
                    "bam_file",
                    {
                        "type": "File",
                        "doc": "Input BAM file, sorted by coordinates",
                        "id": "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#bam_file"
                    }
                )
            ]
        ),
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
            "dummy",
            []
        ),        
        (
            [
                "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sorted_bedgraph_to_bigwig/bigwig_file",
                "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sort_bedgraph/sorted_file"
            ],
            "sort_bedgraph/sorted_file",
            [
                (
                    "sort_bedgraph/sorted_file",
                    "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sort_bedgraph/sorted_file"
                )
            ]
        ),
        (
            [
                "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sorted_bedgraph_to_bigwig/bigwig_file",
                "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sort_bedgraph/sorted_file"
            ],
            "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sort_bedgraph/sorted_file",
            [
                (
                    "sort_bedgraph/sorted_file",
                    "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sort_bedgraph/sorted_file"
                )
            ]
        ),
        (
            [
                "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sorted_bedgraph_to_bigwig/bigwig_file",
                "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sort_bedgraph/sorted_file"
            ],
            "dummy",
            []
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
            "bedgraph_filename",
            [
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
            "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#bedgraph_filename",
            [
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
            "dummy",
            []
        ),
        (
            [
                [
                    "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sorted_bedgraph_to_bigwig/bigwig_file",
                    "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sort_bedgraph/sorted_file"
                ]
            ],
            [
                "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sorted_bedgraph_to_bigwig/bigwig_file",
                "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sort_bedgraph/sorted_file"
            ],
            [
                (
                    [
                        "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sorted_bedgraph_to_bigwig/bigwig_file",
                        "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sort_bedgraph/sorted_file"
                    ],
                    [
                        "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sorted_bedgraph_to_bigwig/bigwig_file",
                        "file:///Users/tester/workflows/bam-bedgraph-bigwig.cwl#sort_bedgraph/sorted_file"
                    ]
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
            "anything that is not exactly the same as input",
            []
        ),
        (
            "file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bigwig_filename",
            "bigwig_filename",
            [
                (
                    "bigwig_filename",
                    "file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bigwig_filename"
                )
            ]
        ),
        (
            "file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bigwig_filename",
            "file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bigwig_filename",
            [
                (
                    "bigwig_filename",
                    "file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bigwig_filename"
                )
            ]
        ),
        (
            "file:///Users/kot4or/workspaces/airflow/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#bigwig_filename",
            "dummy",
            []
        ),
        (
            10,
            10,
            [(10, 10)]
        ),
        (
            10,
            12,
            []
        ),
        (
            [],
            "dummy",
            []
        )
    ]
)
def test_get_items(inputs, target_id, controls):
    results = list(get_items(inputs, target_id))
    assert results == controls
