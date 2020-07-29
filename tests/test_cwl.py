import os
import sys
import shutil
import pytest
import tempfile
import importlib

from ruamel.yaml.comments import CommentedMap
from cwltool.workflow import Workflow
from cwltool.command_line_tool import CommandLineTool
from schema_salad.exceptions import SchemaSaladException

from cwl_airflow.utilities.helpers import (
    get_md5_sum,
    get_absolute_path,
    dump_json,
    get_rootname,
    get_compressed,
    load_yaml,
    get_dir
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
    overwrite_deprecated_dag,
    get_containers,
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
    "task_id, cidfiles, control_containers",
    [
        (
            "bam_to_bedgraph",
            [
                "dummy_1.cid",
                "dummy_2.cid"
            ],
            {
                "43dd79ede44946a1954d27327000d1c013cb39196c096ce70bc158ee7531a557": "dummy_1.cid",
                "000d1c013cb39196c096ce70bc158ee7531a55743dd79ede44946a1954d27327": "dummy_2.cid"
            }
        ),
        (
            "bam_to_bedgraph",
            [
                "dummy_1.cid"
            ],
            {
                "43dd79ede44946a1954d27327000d1c013cb39196c096ce70bc158ee7531a557": "dummy_1.cid"
            }
        ),
        (
            "bam_to_bedgraph",
            [],
            {}
        )
    ]
)
def test_get_containers(task_id, cidfiles, control_containers, monkeypatch):
    temp_home = tempfile.mkdtemp()
    monkeypatch.delenv("AIRFLOW_HOME", raising=False)
    monkeypatch.delenv("AIRFLOW_CONFIG", raising=False)
    monkeypatch.setattr(
        os.path,
        "expanduser",
        lambda x: x.replace("~", temp_home)
    )

    for cidfile in cidfiles:
        shutil.copy(
            os.path.join(DATA_FOLDER, "cid", cidfile),
            get_dir(os.path.join(temp_home, task_id))
        )

    try:
        containers = get_containers({"tmp_folder": temp_home}, task_id)
        control_containers = {
            cid: os.path.join(temp_home, task_id, filename) 
            for cid, filename in control_containers.items()
        }
    except (BaseException, Exception) as err:
        assert False, f"Failed to run test. \n {err}"
    finally:
        shutil.rmtree(temp_home)
    assert control_containers == containers, \
        "Failed to find cidfiles"


@pytest.mark.parametrize(
    "dag_location, workflow_location, control_deprecated_files",
    [
        (
            os.path.join(DATA_FOLDER, "dags", "bam_bedgraph_bigwig_single_old_format.py"),
            os.path.join(DATA_FOLDER, "workflows", "bam-bedgraph-bigwig-single.cwl"),  # need it only to run test
            ["bam_bedgraph_bigwig_single_old_format.py", ".airflowignore"]
        )
    ]
)
def test_overwrite_deprecated_dag(
    dag_location,
    workflow_location,
    control_deprecated_files,
    monkeypatch
):
    temp_home = tempfile.mkdtemp()
    monkeypatch.delenv("AIRFLOW_HOME", raising=False)
    monkeypatch.delenv("AIRFLOW_CONFIG", raising=False)
    monkeypatch.setattr(
        os.path,
        "expanduser",
        lambda x: x.replace("~", temp_home)
    )

    dags_folder = get_dir(
        os.path.join(temp_home, "airflow", "dags")
    )
    dag_location = shutil.copy(
        dag_location,
        os.path.join(
            dags_folder,
            os.path.basename(dag_location)
        )
    )
    workflow_location = shutil.copy(
        workflow_location,
        os.path.join(
            dags_folder,
            os.path.basename(workflow_location)
        )
    )
    deprecated_dags_folder = os.path.join(dags_folder, "deprecated_dags")

    try:

        overwrite_deprecated_dag(
            dag_location=dag_location,
            deprecated_dags_folder=deprecated_dags_folder
        )
        os.remove(workflow_location)                                         # remove workflow file to make sure we are loading compressed workflow content
        spec = importlib.util.spec_from_file_location(
            get_rootname(dag_location),
            dag_location
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        deprecated_dags_folder_content = os.listdir(deprecated_dags_folder)
        with open(
            os.path.join(deprecated_dags_folder, ".airflowignore")
        ) as input_stream:
            airflowignore_content = input_stream.read()

    except (BaseException, Exception) as err:
        assert False, f"Failed to run test. \n {err}"
    finally:
        shutil.rmtree(temp_home)

    assert all(
        deprecated_file in deprecated_dags_folder_content
        for deprecated_file in control_deprecated_files
    ), "Failed to backup DAGs"
    assert control_deprecated_files[0] in airflowignore_content, \
        "Failed to update .airflowignore"


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
        shutil.rmtree(pickle_folder)


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
        shutil.rmtree(temp_home)

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
        shutil.rmtree(pickle_folder)


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
            #  bam-bedgraph-bigwig-single.cwl
            "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 zhXTfFcVnL/gosFZpps\
             /GU8SmShNS4FB6wsEIYqpbGyfu61v/weDmYiG",
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
    if (isinstance(workflow, str)):
        workflow_path = workflow
    else:
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
        shutil.rmtree(pickle_folder)


@pytest.mark.parametrize(
    "job, workflow",
    [
        (
            "bam-bedgraph-bigwig.json",
            ["workflows", "bam-bedgraph-bigwig.cwl"]
        ),
        (
            "bam-bedgraph-bigwig.json",
            #  bam-bedgraph-bigwig-single.cwl
            "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 zhXTfFcVnL/gosFZpps\
             /GU8SmShNS4FB6wsEIYqpbGyfu61v/weDmYiG"
        )
    ]
)
def test_load_job_from_file(job, workflow):
    pickle_folder = tempfile.mkdtemp()
    if (isinstance(workflow, str)):
        workflow_path = workflow
    else:
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
        shutil.rmtree(pickle_folder)


@pytest.mark.parametrize(
    "job, workflow",
    [
        (
            "bam-bedgraph-bigwig.json",
            ["workflows", "dummy.cwl"]
        ),
        (
            "bam-bedgraph-bigwig.json",
            "nonenonenonenonenone"
        ),
        (
            "bam-bedgraph-bigwig.json",
            # bam-bedgraph-bigwig.cwl
            "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\
             m3vwGItZCP"
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
                    "location": "../inputs/chr4_100_mapped_reads.bam"
                },
                "chrom_length_file": {
                    "class": "File",
                    "location": "../inputs/chr_name_length.txt"
                },
                "scale": 1
            },
            #  bam-bedgraph-bigwig-single.cwl
            "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 zhXTfFcVnL/gosFZpps\
             /GU8SmShNS4FB6wsEIYqpbGyfu61v/weDmYiG",
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
    if (isinstance(workflow, str)):
        workflow_path = workflow
    else:
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
        shutil.rmtree(pickle_folder)


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
                    "location": "../inputs/dummy.txt"
                },
                "chrom_length_file": {
                    "class": "File",
                    "location": "../inputs/dummy.txt"
                },
                "scale": 1
            },
            #  bam-bedgraph-bigwig.cwl
            "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\
             m3vwGItZCP",
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


def test_slow_cwl_load_compressed_workflow():
    workflow_tool = slow_cwl_load(
        workflow=os.path.join(
            DATA_FOLDER, "workflows", "bam-bedgraph-bigwig.cwl"
        ),
        only_tool=True
    )
    workflow_tool = slow_cwl_load(
        get_compressed(workflow_tool),
        only_tool=True
    )
    assert isinstance(workflow_tool, CommentedMap)


def test_slow_cwl_load_compressed_raw_workflow():
    workflow_tool = slow_cwl_load(
        get_compressed(
            os.path.join(
                DATA_FOLDER, "workflows", "bam-bedgraph-bigwig-single.cwl"
            )
        ),
        only_tool=True
    )
    assert isinstance(workflow_tool, CommentedMap)


def test_slow_cwl_load_workflow_should_fail():
    with pytest.raises(SchemaSaladException):
        workflow_data = slow_cwl_load(
            workflow=os.path.join(
                DATA_FOLDER, "workflows", "dummy.cwl"
            )
        )


def test_slow_cwl_load_compressed_raw_workflow_should_fail():
    with pytest.raises(SchemaSaladException):
        workflow_tool = slow_cwl_load(
            get_compressed(
                os.path.join(
                    DATA_FOLDER, "workflows", "bam-bedgraph-bigwig.cwl"
                )
            ),
            only_tool=True
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
        shutil.rmtree(pickle_folder)

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
        shutil.rmtree(pickle_folder)

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
    shutil.copy(workflow_path, duplicate_workflow_path)
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
        shutil.rmtree(pickle_folder)

    assert isinstance(workflow_tool, CommentedMap), \
           "Failed to load pickled CWL file"


@pytest.mark.parametrize(
    "workflow",
    [
        (   # bam-bedgraph-bigwig-single.cwl
            "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 zhXTfFcVnL/gosFZpps\
             /GU8SmShNS4FB6wsEIYqpbGyfu61v/weDmYiG"
        )
    ]
)
def test_fast_cwl_load_workflow_from_compressed_cwl(workflow):
    pickle_folder = tempfile.mkdtemp()
    pickled_workflow_path = get_md5_sum(workflow) + ".p"
    try:
        workflow_tool = fast_cwl_load(
            workflow=workflow,
            cwl_args={"pickle_folder": pickle_folder}
        )
        pickle_folder_content = os.listdir(pickle_folder)
    except BaseException as err:
        assert False, f"Failed to run test. \n {err}"
    finally:
        shutil.rmtree(pickle_folder)

    assert isinstance(workflow_tool, CommentedMap), \
           "Failed to parse CWL file"
    assert pickled_workflow_path in pickle_folder_content, \
           "Failed to pickle CWL file"


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
        except (FileNotFoundError, SchemaSaladException) as err:
            assert False, f"Should raise because workflow wasn't found. \n {err}"
        finally:
            shutil.rmtree(pickle_folder)


@pytest.mark.parametrize(
    "workflow",
    [
        (
            "nonenonenone"
        ),
        (   # bam-bedgraph-bigwig.cwl
            "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\
             m3vwGItZCP"
        )

    ]
)
def test_fast_cwl_load_workflow_from_compressed_cwl_should_fail(workflow):
    pickle_folder = tempfile.mkdtemp()
    workflow_path = os.path.join(DATA_FOLDER, *workflow)
    with pytest.raises(AssertionError):
        try:
            workflow_tool = fast_cwl_load(
                workflow=workflow,
                cwl_args={"pickle_folder": pickle_folder}
            )
        except (FileNotFoundError, SchemaSaladException) as err:
            assert False, \
                f"Should raise because workflow didn't include runs or didn't exist. \n {err}"
        finally:
            shutil.rmtree(pickle_folder)


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
