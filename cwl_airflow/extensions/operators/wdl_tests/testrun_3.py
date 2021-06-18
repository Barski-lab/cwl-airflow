from cwl_airflow.extensions.wdldag import WDLDAG
dag = WDLDAG(workflow="/Users/nickluckey/Documents/wdl-workspace/cwl-airflow/tests/data/workflows/classify_single.wdl", dag_id="classify_single")