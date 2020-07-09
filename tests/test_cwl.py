import os
import sys
import copy
import pytest
import tempfile

from shutil import rmtree, copy
from ruamel.yaml.comments import CommentedMap
from cwltool.workflow import Workflow
from cwltool.command_line_tool import CommandLineTool
from schema_salad.exceptions import SchemaSaladException

from cwl_airflow.utilities.helpers import (
    get_md5_sum,
    get_absolute_path,
    dump_json,
    get_rootname
)
from cwl_airflow.utilities.cwl import (
    fast_cwl_load,
    slow_cwl_load,
    fast_cwl_step_load,
    load_job,
    get_items,
    get_short_id,
    execute_workflow_step,
    embed_all_runs,
    convert_to_workflow,
    get_default_cwl_args,
    CWL_TMP_FOLDER,
    CWL_OUTPUTS_FOLDER,
    CWL_PICKLE_FOLDER,
    CWL_USE_CONTAINER,
    CWL_NO_MATCH_USER,
    CWL_SKIP_SCHEMAS,
    CWL_STRICT,
    CWL_QUIET,
    CWL_RM_TMPDIR,
    CWL_MOVE_OUTPUTS
)


DATA_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
if sys.platform == "darwin":                                                    # docker has troubles of mounting /var/private on macOs
    tempfile.tempdir = "/private/tmp"


@pytest.mark.parametrize(
    "workflow, job",
    [
        (
            ["tools", "bedtools-genomecov.cwl"],
            "bedtools-genomecov.json"
        ),
        (
            ["tools", "linux-sort.cwl"],
            "linux-sort.json"
        ),
        (
            ["tools", "ucsc-bedgraphtobigwig.cwl"],
            "ucsc-bedgraphtobigwig.json"
        )
    ]
)
def test_convert_to_workflow(workflow, job):
    pickle_folder = tempfile.mkdtemp()

    command_line_tool = slow_cwl_load(
        workflow = os.path.join(DATA_FOLDER, *workflow),
        only_tool=True
    )
    converted_workflow_path = os.path.join(pickle_folder, "workflow.cwl")
    workflow_tool = convert_to_workflow(
        command_line_tool=command_line_tool,
        location=converted_workflow_path
    )
    try:
        job_data = load_job(
            workflow=converted_workflow_path,
            job=os.path.join(DATA_FOLDER, "jobs", job),
            cwl_args={"pickle_folder": pickle_folder}
        )
        job_data["tmp_folder"] = pickle_folder
        step_outputs, step_report = execute_workflow_step(
            workflow=converted_workflow_path,
            task_id=get_rootname(command_line_tool["id"]),
            job_data=job_data,
            cwl_args={"pickle_folder": pickle_folder}
        )
    except BaseException as err:
        assert False, f"Failed either to run test or execute workflow. \n {err}"
    finally:
        rmtree(pickle_folder)


@pytest.mark.parametrize(
    "control_defaults",
    [
        (
            {
                "tmp_folder": CWL_TMP_FOLDER,
                "outputs_folder": CWL_OUTPUTS_FOLDER,
                "pickle_folder": CWL_PICKLE_FOLDER,
                "use_container": CWL_USE_CONTAINER,
                "no_match_user": CWL_NO_MATCH_USER,
                "skip_schemas": CWL_SKIP_SCHEMAS,
                "strict": CWL_STRICT,
                "quiet": CWL_QUIET,
                "rm_tmpdir": CWL_RM_TMPDIR,
                "move_outputs": CWL_MOVE_OUTPUTS
            }
        )
    ]
)
def test_get_default_cwl_args(monkeypatch, control_defaults):
    temp_home = tempfile.mkdtemp()
    monkeypatch.delenv("AIRFLOW_HOME", raising=False)
    monkeypatch.delenv("AIRFLOW_CONFIG", raising=False)
    monkeypatch.setattr(
        os.path,
        "expanduser",
        lambda x: x.replace("~", temp_home)
    )

    try:
        required_cwl_args = get_default_cwl_args()
    except (BaseException, Exception) as err:
        assert False, f"Failed to run test. \n {err}"
    finally:
        rmtree(temp_home)

    assert all(
        required_cwl_args[key] == contol_value
        for key, contol_value in control_defaults.items()
    ), "Failed to set proper defaults"


@pytest.mark.parametrize(
    "workflow, job, task_id",
    [
        (
            ["workflows", "bam-bedgraph-bigwig.cwl"],
            "bam-to-bedgraph-step.json",
            "bam_to_bedgraph"
        ),
        (
            ["workflows", "bam-bedgraph-bigwig-single.cwl"],
            "bam-to-bedgraph-step.json",
            "bam_to_bedgraph"
        ),
        (
            ["workflows", "bam-bedgraph-bigwig-subworkflow.cwl"],
            "bam-bedgraph-bigwig.json",
            "subworkflow"
        )
    ]
)
def test_embed_all_runs(workflow, job, task_id):
    pickle_folder = tempfile.mkdtemp()
    packed_workflow_path = os.path.join(pickle_folder, "packed.cwl")
    embed_all_runs(
        workflow_tool=slow_cwl_load(
            workflow = os.path.join(DATA_FOLDER, *workflow),
            only_tool=True
        ), 
        location=packed_workflow_path
    )
    try:
        job_data = load_job(
            workflow=packed_workflow_path,
            job=os.path.join(DATA_FOLDER, "jobs", job),
            cwl_args={"pickle_folder": pickle_folder}
        )
        job_data["tmp_folder"] = pickle_folder
        step_outputs, step_report = execute_workflow_step(
            workflow=packed_workflow_path,
            task_id=task_id,
            job_data=job_data,
            cwl_args={"pickle_folder": pickle_folder}
        )
    except BaseException as err:
        assert False, f"Failed either to run test or execute workflow. \n {err}"
    finally:
        rmtree(pickle_folder)


@pytest.mark.parametrize(
    "long_id, only_step_name, only_id, control",
    [
        (
            "file:///Users/tester/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#sorted_bedgraph_to_bigwig/output_filename",
            None,
            None,
            "sorted_bedgraph_to_bigwig/output_filename"
        ),
        (
            "file:///Users/tester/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#sorted_bedgraph_to_bigwig/output_filename",
            True,
            None,
            "sorted_bedgraph_to_bigwig"
        ),
        (
            "file:///Users/tester/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#sorted_bedgraph_to_bigwig/output_filename",
            None,
            True,
            "output_filename"
        ),
        (
            "file:///Users/tester/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig.cwl#sorted_bedgraph_to_bigwig/output_filename",
            True,
            True,
            ""
        ),
        (
            "sorted_bedgraph_to_bigwig/output_filename",
            None,
            None,
            "sorted_bedgraph_to_bigwig/output_filename"
        ),
        (
            "sorted_bedgraph_to_bigwig/output_filename",
            True,
            None,
            "sorted_bedgraph_to_bigwig"
        ),
        (
            "sorted_bedgraph_to_bigwig/output_filename",
            None,
            True,
            "output_filename"
        ),
        (
            "sorted_bedgraph_to_bigwig/output_filename",
            True,
            True,
            ""
        ),
        (
            "file:///Users/tester/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig-single.cwl#bam_to_bedgraph/9d930026-6d03-4cef-aa56-d07616e1e739/genome_coverage_file",
            None,
            None,
            "bam_to_bedgraph/genome_coverage_file"
        ),
        (
            "file:///Users/tester/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig-single.cwl#bam_to_bedgraph/9d930026-6d03-4cef-aa56-d07616e1e739/genome_coverage_file",
            True,
            None,
            "bam_to_bedgraph"
        ),
        (
            "file:///Users/tester/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig-single.cwl#bam_to_bedgraph/9d930026-6d03-4cef-aa56-d07616e1e739/genome_coverage_file",
            None,
            True,
            "genome_coverage_file"
        ),
        (
            "file:///Users/tester/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig-single.cwl#bam_to_bedgraph/9d930026-6d03-4cef-aa56-d07616e1e739/genome_coverage_file",
            True,
            True,
            ""
        ),
        (
            "bam_to_bedgraph/9d930026-6d03-4cef-aa56-d07616e1e739/genome_coverage_file",
            None,
            None,
            "bam_to_bedgraph/genome_coverage_file"
        ),
        (
            "bam_to_bedgraph/9d930026-6d03-4cef-aa56-d07616e1e739/genome_coverage_file",
            True,
            None,
            "bam_to_bedgraph"
        ),
        (
            "bam_to_bedgraph/9d930026-6d03-4cef-aa56-d07616e1e739/genome_coverage_file",
            None,
            True,
            "genome_coverage_file"
        ),
        (
            "bam_to_bedgraph/9d930026-6d03-4cef-aa56-d07616e1e739/genome_coverage_file",
            True,
            True,
            ""
        ),
        (
            "output_filename",
            None,
            None,
            "output_filename"
        ),
        (
            "output_filename",
            True,
            None,
            "output_filename"
        ),
        (
            "output_filename",
            None,
            True,
            "output_filename"
        ),
        (
            "output_filename",
            True,
            True,
            "output_filename"
        )
    ]
)
def test_get_short_id(long_id, only_step_name, only_id, control):
    result = get_short_id(long_id, only_step_name, only_id)
    assert result == control, "Test failed"


# It's also indirect testing of fast_cwl_step_load
@pytest.mark.parametrize(
    "workflow, job, task_id",
    [
        (
            ["workflows", "bam-bedgraph-bigwig.cwl"],
            "bam-to-bedgraph-step.json",
            "bam_to_bedgraph"
        ),
        (
            ["workflows", "bam-bedgraph-bigwig.cwl"],
            "sort-bedgraph-step.json",
            "sort_bedgraph"
        ),
        (
            ["workflows", "bam-bedgraph-bigwig.cwl"],
            "sorted-bedgraph-to-bigwig-step.json",
            "sorted_bedgraph_to_bigwig"
        ),
        (
            ["workflows", "bam-bedgraph-bigwig-single.cwl"],
            "bam-to-bedgraph-step.json",
            "bam_to_bedgraph"
        ),
        (
            ["workflows", "bam-bedgraph-bigwig-single.cwl"],
            "sort-bedgraph-step.json",
            "sort_bedgraph"
        ),
        (
            ["workflows", "bam-bedgraph-bigwig-single.cwl"],
            "sorted-bedgraph-to-bigwig-step.json",
            "sorted_bedgraph_to_bigwig"
        ),
        (
            ["workflows", "bam-bedgraph-bigwig-subworkflow.cwl"],
            "bam-bedgraph-bigwig.json",
            "subworkflow"
        )
    ]
)
def test_execute_workflow_step(workflow, job, task_id):
    pickle_folder = tempfile.mkdtemp()
    workflow_path = os.path.join(DATA_FOLDER, *workflow)
    job_path = os.path.join(DATA_FOLDER, "jobs", job)
    cwl_args = {"pickle_folder": pickle_folder}

    job_data = load_job(
        workflow=workflow_path,
        job=job_path,
        cwl_args=cwl_args
    )
    job_data["tmp_folder"] = pickle_folder                  # need manually add "tmp_folder"

    try:
        step_outputs, step_report = execute_workflow_step(
            workflow=workflow_path,
            task_id=task_id,
            job_data=job_data,
            cwl_args=cwl_args
        )
    except BaseException as err:
        assert False, f"Failed either to run test or execute workflow. \n {err}"
    finally:
        rmtree(pickle_folder)


@pytest.mark.parametrize(
    "job, workflow",
    [
        (
            "bam-bedgraph-bigwig.json",
            ["workflows", "bam-bedgraph-bigwig.cwl"]
        )
    ]
)
def test_load_job_from_file(job, workflow):
    pickle_folder = tempfile.mkdtemp()
    workflow_path = os.path.join(DATA_FOLDER, *workflow)
    job_path = os.path.join(DATA_FOLDER, "jobs", job)
    try:
        job_data = load_job(
            workflow=workflow_path,
            job=job_path,
            cwl_args={"pickle_folder": pickle_folder}
        )
    except BaseException as err:
        assert False, f"Failed to load job from file"
    finally:
        rmtree(pickle_folder)


@pytest.mark.parametrize(
    "job, workflow",
    [
        (
            "bam-bedgraph-bigwig.json",
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
    pickle_folder = tempfile.mkdtemp()
    workflow_path = os.path.join(DATA_FOLDER, *workflow)
    try:
        job_data = load_job(
            workflow=workflow_path,
            job=job,
            cwl_args={"pickle_folder": pickle_folder},
            cwd=cwd
        )
    except BaseException as err:
        assert False, f"Failed to load job from parsed object"
    finally:
        rmtree(pickle_folder)


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
    workflow_data = slow_cwl_load(
        workflow = os.path.join(
            DATA_FOLDER, "workflows", "bam-bedgraph-bigwig.cwl"
        )
    )
    assert isinstance(workflow_data, Workflow)


def test_slow_cwl_load_command_line_tool():
    command_line_tool_data = slow_cwl_load(
        workflow = os.path.join(
            DATA_FOLDER, "tools", "linux-sort.cwl"
        )
    )
    assert isinstance(command_line_tool_data, CommandLineTool)


def test_slow_cwl_load_reduced_workflow():
    workflow_tool = slow_cwl_load(
        workflow=os.path.join(
            DATA_FOLDER, "workflows", "bam-bedgraph-bigwig.cwl"
        ),
        only_tool=True
    )
    assert isinstance(workflow_tool, CommentedMap)


def test_slow_cwl_load_reduced_command_line_tool():
    command_line_tool = slow_cwl_load(
        workflow=os.path.join(
            DATA_FOLDER, "tools", "linux-sort.cwl"
        ),
        only_tool=True
    )
    assert isinstance(command_line_tool, CommentedMap)


def test_slow_cwl_load_parsed_workflow():
    workflow_tool = slow_cwl_load(
        workflow=os.path.join(
            DATA_FOLDER, "workflows", "bam-bedgraph-bigwig.cwl"
        ),
        only_tool=True
    )
    workflow_tool = slow_cwl_load(workflow_tool)
    assert isinstance(workflow_tool, CommentedMap)


def test_slow_cwl_load_workflow_should_fail():
    with pytest.raises(SchemaSaladException):
        workflow_data = slow_cwl_load(
            workflow=os.path.join(
                DATA_FOLDER, "workflows", "dummy.cwl"
            )
        )


@pytest.mark.parametrize(
    "workflow",
    [
        (
            ["workflows", "bam-bedgraph-bigwig.cwl"]
        ),
        (
            ["tools", "linux-sort.cwl"]
        )
    ]
)
def test_fast_cwl_load_workflow_from_cwl(workflow):
    pickle_folder = tempfile.mkdtemp()
    workflow_path = os.path.join(DATA_FOLDER, *workflow)
    pickled_workflow_path = get_md5_sum(workflow_path) + ".p"
    try:
        workflow_tool = fast_cwl_load(
            workflow=workflow_path,
            cwl_args={"pickle_folder": pickle_folder}
        )
        pickle_folder_content = os.listdir(pickle_folder)
    except BaseException as err:
        assert False, f"Failed to run test. \n {err}"
    finally:
        rmtree(pickle_folder)

    assert isinstance(workflow_tool, CommentedMap), \
           "Failed to parse CWL file"
    assert pickled_workflow_path in pickle_folder_content, \
           "Failed to pickle CWL file"


@pytest.mark.parametrize(
    "workflow",
    [
        (
            ["workflows", "bam-bedgraph-bigwig.cwl"]
        ),
        (
            ["tools", "linux-sort.cwl"]
        )
    ]
)
def test_fast_cwl_load_workflow_from_parsed(workflow):
    pickle_folder = tempfile.mkdtemp()
    workflow_path = os.path.join(DATA_FOLDER, *workflow)
    pickled_workflow_path = get_md5_sum(workflow_path) + ".p"
    try:
        workflow_tool = fast_cwl_load(
            workflow=workflow_path,
            cwl_args={"pickle_folder": pickle_folder}
        )
        workflow_tool = fast_cwl_load(
            workflow=workflow_tool,
            cwl_args={"pickle_folder": pickle_folder}
        )
    except BaseException as err:
        assert False, f"Failed to run test. \n {err}"
    finally:
        rmtree(pickle_folder)

    assert isinstance(workflow_tool, CommentedMap), \
           "Failed to parse CWL file"


@pytest.mark.parametrize(
    "workflow",
    [
        (
            ["workflows", "bam-bedgraph-bigwig.cwl"]
        ),
        (
            ["tools", "linux-sort.cwl"]
        )
    ]
)
def test_fast_cwl_load_workflow_from_pickle(workflow):
    pickle_folder = tempfile.mkdtemp()
    workflow_path = os.path.join(DATA_FOLDER, *workflow)
    duplicate_workflow_path = os.path.join(pickle_folder, workflow[-1])  # will fail if parsed directly
    copy(workflow_path, duplicate_workflow_path)
    try:
        workflow_tool = fast_cwl_load(                                   # should result in creating pickled file
            workflow=workflow_path,
            cwl_args={"pickle_folder": pickle_folder}
        )
        workflow_tool = fast_cwl_load(                                   # should load from pickled file
            workflow=duplicate_workflow_path,
            cwl_args={"pickle_folder": pickle_folder}
        )
    except BaseException as err:
        assert False, f"Failed to run test. \n {err}"
    finally:
        rmtree(pickle_folder)

    assert isinstance(workflow_tool, CommentedMap), \
           "Failed to load pickled CWL file"


@pytest.mark.parametrize(
    "workflow",
    [
        (
            ["workflows", "dummy.cwl"]
        )
    ]
)
def test_fast_cwl_load_workflow_from_cwl_should_fail(workflow):
    pickle_folder = tempfile.mkdtemp()
    workflow_path = os.path.join(DATA_FOLDER, *workflow)
    with pytest.raises(AssertionError):
        try:
            workflow_tool = fast_cwl_load(
                workflow=workflow_path,
                cwl_args={"pickle_folder": pickle_folder}
            )
        except FileNotFoundError as err:
            assert False, f"Should raise because workflow wasn't found. \n {err}"
        finally:
            rmtree(pickle_folder)


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
            [
                "file:///id/id/id/bam-bedgraph-bigwig.cwl#sorted_bedgraph_to_bigwig/bigwig_file",
                "file:///id/id/id//bam-bedgraph-bigwig.cwl#sort_bedgraph/sorted_file"
            ],
            None,
            [
                (
                    "sorted_bedgraph_to_bigwig/bigwig_file",
                    "file:///id/id/id/bam-bedgraph-bigwig.cwl#sorted_bedgraph_to_bigwig/bigwig_file",
                ), 
                (
                    "sort_bedgraph/sorted_file",
                    "file:///id/id/id//bam-bedgraph-bigwig.cwl#sort_bedgraph/sorted_file"
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
