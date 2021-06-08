from cwl_airflow.extensions.cwldag import CWLDAG
dag = CWLDAG(workflow="/Users/nickluckey/Documents/wdl-workspace/cwl-airflow/tests/data/workflows/bam-bedgraph-bigwig-single.cwl", dag_id="bam-bedgraph-bigwig-single")
print(dag)