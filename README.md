# cwl-airflow

### About
Python package to extend **[Apache-Airflow 1.8.2](https://github.com/apache/incubator-airflow)**
functionality with **[CWL v1.0](http://www.commonwl.org/v1.0/)** support.

### Installation
1. Make sure your system satisfies the following criterias:
      - Ubuntu 16.04
        - Python 2.7.12
        - pip 9.0.1 (pip install --upgrade pip)
        - setuptools 38.4.0 (pip install setuptools)
        - libmysqlclient-dev (sudo apt-get install libmysqlclient-dev)
        - zip 3.0
        - docker
      - macOS Hight Sierra 10.13.2
        - Python 2.7.12
        - pip 9.0.1
        - setuptools 38.4.0
        - zip 3.0
        - docker
2. Install the latest version of `cwl-airflow` from source
      ```sh
      $ git clone --branch v1.0.0 https://github.com/Barski-lab/cwl-airflow.git
      $ cd cwl-airflow
      $ pip install . --user
      ```
      > To clone input data for workflow testing use 
      `git clone --branch v1.0.0 --recursive https://github.com/Barski-lab/cwl-airflow.git`
       
   If **[Apache-Airflow](https://github.com/apache/incubator-airflow)** or
   **[cwltool](http://www.commonwl.org/ "cwltool main page")** aren't installed,
   it will be done automatically with recommended versions:
   **Apache-Airflow v1.8.2**, **cwltool 1.0.20171107133715**

3. If required, add **[extra packages](https://airflow.incubator.apache.org/installation.html#extra-packages)**
   for extending Airflow functionality with MySQL, PostgreSQL backend support etc.

### Preparing workflow and job files
1. All workflow descriptor files should be placed in a folder set as ***cwl_workflows*** in Airflow configuration file. The structure of this folder is arbitrary.

2. Folder ***cwl_jobs*** from the same configuration file is used to store input parameters files (i.e job files) and should have the following structure
```
├── jobs
│   ├── fail
│   ├── new
│   ├── running
│   └── success
```
All the job files scheduled to be processed should be placed in ***new*** subfolder. Depending on the current execution state the job file can be moved to one of the following folders: ***fail***, ***running***, ***success***

3. To allow automatically fetch CWL descriptor file by job's filename, follow naming rule
  ```
  [identical].cwl                 - workflow descriptor filename
  [identical][arbitrary].json     - input parameters filename
  ```
  where [identical] part of the name defines the correspondence between workflow and job files.

  > Pay attention, if you have two or more workflow descriptor files with identical names, but in different subfolders of ***cwl_workflows***, the newest one will be used.

4. Job file may include additional fields which in case of ***output_folder*** and ***tmp_folder***
redefines parameters from ***airflow.cfg***.
```
{
    "uid": "arbitrary unique id, which will be used for current workflow run",
    "output_folder": "path to the folder to save results",
    "tmp_folder": "path to the folder to save temporary calculation results",
    "author": "Author of a the experiment. Default: CWL-Airflow"
}
```
> Pay attention, ***output_folder*** and ***tmp_folder*** may be set as the path realtive
to job file location 

### Running workflow

#### Automatic mode
1. Put CWL descriptor file and all tools which it includes into ***cwl_workflows*** folder.
All input parameters files should be placed in subfolder ***new*** of  ***cwl_jobs***.

2. Run Airflow scheduler:
  ```sh
  $ airflow scheduler
  ```
  > Pay attention, you can use [cwl-airflow-cli](https://github.com/Barski-lab/airflow_cwl_cli)
  to make it even more easy then it is.

#### Manual mode
Use `cwl-airflow-runner` with explicitly specified CWL descriptor and input parameters files.
```bash
   cwl-airflow-runner WORKFLOW JOB
```
If necessary, set additional arguments following the `cwl-airflow-runner --help` information.
> When running on macOS, make sure yor docker or docker-machine has access to `$TMPDIR`. If necessary set `--tmp-outdir-prefix` and `--tmpdir-prefix` parameters to point location available for your docker.
<details> 
  <summary>cwl-airflow-runner --help</summary>
  
        usage: cwl-airflow-runner [-h] [-t TASK_REGEX] [-m] [-l] [-x] [-a] [-i] [-I]
                                  [--pool POOL] [-dr] [--outdir OUTDIR]
                                  [--tmp-folder TMP_FOLDER]
                                  [--tmpdir-prefix TMPDIR_PREFIX]
                                  [--tmp-outdir-prefix TMP_OUTDIR_PREFIX] [--quiet]
                                  [--ignore-def-outdir]
                                  workflow job
        
        CWL-Airflow
        
        positional arguments:
          workflow
          job
        
        optional arguments:
          -h, --help            show this help message and exit
          -t TASK_REGEX, --task_regex TASK_REGEX
                                The regex to filter specific task_ids to backfill
                                (optional)
          -m, --mark_success    Mark jobs as succeeded without running them
          -l, --local           Run the task using the LocalExecutor
          -x, --donot_pickle    Do not attempt to pickle the DAG object to send over
                                to the workers, just tell the workers to run their
                                version of the code.
          -a, --include_adhoc   Include dags with the adhoc parameter.
          -i, --ignore_dependencies
                                Skip upstream tasks, run only the tasks matching the
                                regexp. Only works in conjunction with task_regex
          -I, --ignore_first_depends_on_past
                                Ignores depends_on_past dependencies for the first set
                                of tasks only (subsequent executions in the backfill
                                DO respect depends_on_past).
          --pool POOL           Resource pool to use
          -dr, --dry_run        Perform a dry run
          --outdir OUTDIR       Output folder to save results
          --tmp-folder TMP_FOLDER
                                Temp folder to store data between execution of airflow
                                tasks/steps
          --tmpdir-prefix TMPDIR_PREFIX
                                Path prefix for temporary directories
          --tmp-outdir-prefix TMP_OUTDIR_PREFIX
                                Path prefix for intermediate output directories
          --quiet               Print only workflow execultion results
          --ignore-def-outdir   Disable default output directory to be set to current
                                directory. Use OUTPUT_FOLDER from Airflow
                                configuration file instead
</details>


### Collecting output
  All output files will be saved into subfolder of **output_folder**
  with the name corresponding to the job filename.
