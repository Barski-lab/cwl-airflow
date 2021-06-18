from cwl_airflow.extensions.wdldag import WDLDAG
dag = WDLDAG(workflow="/Users/nickluckey/Documents/wdl-workspace/cwl-airflow/tests/data/workflows/align_and_plot.wdl", dag_id="align-and-plot")