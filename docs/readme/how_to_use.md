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

The most convenient way to **manually trigger** DAG execution is using Airflow Webserver. Input parameters can be set in the **job** field of the running configuration as it is displayed on the pictures below.

![](../images/trigger_1.jpg)
![](../images/trigger_2.jpg)


To start Airflow Scheduler (**don't** run it if *cwl-airflow submit* is used with *-r* argument)
```bash
airflow scheduler
```
To start Airflow Webserver (by default it is accessible from your [localhost:8080](http://127.0.0.1:8080/admin/))
```bash
airflow webserver
```

Please note that both Airflow Scheduler and Webserver can be adjusted through the configuration file
(default location is *~/airflow/airflow.cfg*). Refer to the [official documentation](https://airflow.apache.org/howto/set-config.html) 
 
## Demo mode

- To get the list of the available demo workflows
    ```bash
    $ cwl-airflow demo --list
    ```
- To submit the specific demo workflow from the list
(workflow will not be run until Airflow Scheduler is started separately)
    ```bash
    $ cwl-airflow demo super-enhancer.cwl
    ```
    Depending on your Airflow configuration it may require some time for Airflow Scheduler
    and Webserver to pick up new DAGs. Consider using `cwl-airflow init -r 5 -w 4` to make Airflow Webserver react faster on all
    newly created DAGs.

- To submit all demo workflows from the list
(workflows will not be run until Airflow Scheduler is started separately)
    ```bash
    $ cwl-airflow demo --manual
    ```
    Before submitting demo workflows the Jobs folder will be automatically cleaned.
    
- To execute all available demo workflows (automatically starts Airflow Scheduler and Airflow Webserver)
    ```bash
    $ cwl-airflow demo --auto
    ```
    
Optional parameters:

| Flag | Description                                                                                            | Default           |
|------|--------------------------------------------------------------------------------------------------------|-------------------|
| -o   | path to the folder where all the output files should be moved after successful workflow execution, str | current directory |
| -t   | path to the temporary folder for storing intermediate results, str                                     | */tmp/cwlairflow* |
| -u   | ID for DAG's unique identifier generation, str. Ignored when *--list* or *--auto* is used              | random uuid       |


## Running sample ChIP-Seq-SE workflow

This [ChIP-Seq-SE workflow](https://barski-lab.github.io/ga4gh_challenge/) is a CWL version of
a Python pipeline from [BioWardrobe](https://github.com/Barski-lab/biowardrobe/wiki).
It starts by extracting an input FASTQ file (if it was compressed). Next step runs
[BowTie](http://bowtie-bio.sourceforge.net/index.shtml) to perform alignment to a reference genome,
resulting in an unsorted SAM file. The SAM file is then sorted and indexed with
[Samtools](http://samtools.sourceforge.net/) to obtain a BAM file and a BAI index.
Next [MACS2](https://github.com/taoliu/MACS/wiki) is used to call peaks and to estimate fragment size.
In the last few steps, the coverage by estimated fragments is calculated from the BAM file and is
reported in bigWig format. The pipeline also reports statistics, such as read quality, peak number
and base frequency, as long as other troubleshooting information using tools such as
[Fastx-toolkit](http://hannonlab.cshl.edu/fastx_toolkit/) and
[Bamtools](https://github.com/pezmaster31/bamtools).

To get sample workflow with input data
```bash
$ git clone --recursive https://github.com/Barski-lab/ga4gh_challenge.git --branch v0.0.5
$ ./ga4gh_challenge/data/prepare_inputs.sh
```
Please, be patient it may take some time to clone submodule with input data.
Runing the script *prepare_inputs.sh* will uncompress input FASTQ file.

To submit worflow for execution
```bash
cwl-airflow submit ga4gh_challenge/biowardrobe_chipseq_se.cwl ga4gh_challenge/biowardrobe_chipseq_se.yaml
```
To start Airflow Scheduler (**don't** run it if *cwl-airflow submit* is used with *-r* argument)
```bash
airflow scheduler
```
To start Airflow web interface (by default it is accessible from your [localhost:8080](http://127.0.0.1:8080/admin/))
```bash
airflow webserver
```

Pipeline was tested with
- macOS 10.13.6 (High Sierra)
- Docker
  * Engine: 18.06.0-ce
  * Machine: 0.15.0
  * Preferences
    * CPUs: 4
    * Memory: 2.0 GiB
    * Swap: 1.0 GiB
- Elapsed time: 23 min (may vary depending on you Internet connection bandwidth,
  especially when pipeline is run for the first time and all Docker images
  are being fetched from DockerHub)

## API

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
