#!/usr/bin/env python3
from cwl_airflow import CWLDAG, CWLJobDispatcher, CWLJobGatherer
dag = CWLDAG(cwl_workflow="bam-bedgraph-bigwig-single.cwl", dag_id="bam_bedgraph_bigwig_single_old_format")
dag.create()
dag.add(CWLJobDispatcher(dag=dag), to='top')
dag.add(CWLJobGatherer(dag=dag), to='bottom')

# this DAG is not runnable. It should be updated to the new format