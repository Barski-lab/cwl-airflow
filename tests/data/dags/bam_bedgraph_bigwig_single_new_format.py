#!/usr/bin/env python3
from cwl_airflow.extensions.cwldag import CWLDAG
dag = CWLDAG(
    workflow="bam-bedgraph-bigwig-single.cwl",
    dag_id="bam_bedgraph_bigwig_single_new_format"
)

# this DAG is not runnable. Workflow should have absolute path