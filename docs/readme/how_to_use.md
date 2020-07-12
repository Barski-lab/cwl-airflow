# How to use

## Initial configuration

Before using **CWL-airflow** it should be configured with `cwl-airflow init`

```
$ cwl-airflow init --help

usage: cwl-airflow init [-h] [--home HOME] [--config CONFIG]

optional arguments:
  -h, --help       show this help message and exit
  --home HOME      Set path to Airflow home directory. Default: first try
                   AIRFLOW_HOME then '~/airflow'
  --config CONFIG  Set path to Airflow configuration file. Default: first try
                   AIRFLOW_CONFIG then '[airflow home]/airflow.cfg'
```

**Init command will run the following steps** for the specified `--home` and `--config` parameters:
- Call `airflow initdb`
- Update `airflow.cfg` to hide paused DAGs, skip loading example DAGs and **do not** pause newly created DAGs 
- Add new connection `process_report` to report DAG's execution progress and results to `http://localhost:3070` (URL is currently hardcoded)
- Put **clean_dag_run.py** into the DAGs folder (later its functions will be moved to API)

**Optionally**, you can update your **airflow.cfg** with `[cwl]` section setting the following configuration parameters:

```ini
[cwl]

# Temp folder to keep intermediate workflow execution data.
# Default: AIRFLOW_HOME/cwl_tmp_folder
tmp_folder =

# Output folder to save workflow execution results.
# Default: AIRFLOW_HOME/cwl_outputs_folder
outputs_folder = 

# Folder to keep pickled workflows for fast workflow loading.
# Default: AIRFLOW_HOME/cwl_pickle_folder
pickle_folder = 

# Boolean parameter to force using docker for workflow step execution.
# Default: True
use_container = 

# Boolean parameter to disable passing the current user id to "docker run --user".
# Default: False
no_match_user = 
```
  
## Adding a pipeline

The easiest way to add a new pipeline to CWL-Airflow is to put the following python script into your DAGs folder.
```python
 #!/usr/bin/env python3
from cwl_airflow.extensions.cwldag import CWLDAG
dag = CWLDAG(
    workflow="/absolute/path/to/workflow.cwl",
    dag_id="my_dag_name"
)
```
As `CWLDAG` class was inherited from `DAG`, additional arguments, such as `default_args`, can be provided. The latter can include `cwl` section similar to the one from **airflow.cfg** file, but with lower priority.

**After adding a new DAG**, Airflow Scheduler will load it (by default if happens **every 5 minutes**) and the DAG can be run.

## Executing a pipeline

The most convenient way to **manually execute** DAG is to trigger it in **Airflow UI**. Input parameters can be set in the **job** field of the running configuration.

![](../images/trigger_1.jpg)
![](../images/trigger_2.jpg)

Alternatively, DAGs can be triggered through the **Airflow CLI** with the JSON input paramerers file.

```sh
airflow trigger_dag --conf "{\"job\":$(cat ./bam-bedgraph-bigwig.json)}" bam-bedgraph-bigwig
```

## Using a API

Besides built-in API, provided by Airflow Webserver, CWL-Airflow allows to run API server separately.

To start API server run the following command
```sh
$ cwl-airflow apiserver
```

Optional parameters:

| Flag   | Description            | Default   |
| ------ | ---------------------- | --------- |
| --port | Port to run API server | 8080      |
| --host | Host to run API server | 127.0.0.1 |

Every API endpoint belongs to one of the following groups:

- Airflow (mirrors Airflow console functionality)
- AirflowLegacy (mirrors particular functions from the original Airflow webserver API)
- WorkflowExecutionService (implements main functionality of [WES](https://github.com/ga4gh/workflow-execution-service-schemas))

**For detailed API specification, please follow the link on [SwaggerHub](https://app.swaggerhub.com/apis/michael-kotliar/cwl_airflow_workflow_execution_service/1.0.0)**
