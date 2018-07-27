[![Build Status](https://travis-ci.org/Barski-lab/cwl-airflow.svg?branch=master)](https://travis-ci.org/Barski-lab/cwl-airflow) -  **Travis CI**  
[![Build Status](https://ci.commonwl.org/buildStatus/icon?job=airflow-conformance)](https://ci.commonwl.org/job/airflow-conformance) - **CWL conformance tests**  

# cwl-airflow

Python package to extend **[Apache-Airflow 1.9.0](https://github.com/apache/incubator-airflow)**
functionality with **[CWL v1.0](http://www.commonwl.org/v1.0/)** support.
_________________
### Try it out
1. Install *cwl-airflow*
    ```sh
    $ pip3 install cwl-airflow --user --find-links https://michael-kotliar.github.io/cwl-airflow-wheels/
    ```
2. Init configuration
    ```sh
    $ cwl-airflow init
    ```
3. Run *demo*
    ```sh
    $ cwl-airflow demo --auto
    ```
4. When you see in the console output that Airflow Webserver is started, open the provided link 

_________________

### Installation requirements

- Ubuntu 16.04.4
- python 3.5.2
- pip3
  ```bash
    wget https://bootstrap.pypa.io/get-pip.py
    python3 get-pip.py --user
  ```
- setuptools
  ```
  pip3 install setuptools --user
  ```
- docker
  ```
  sudo apt-get update
  sudo apt-get install apt-transport-https ca-certificates curl software-properties-common
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
  sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
  sudo apt-get update
  sudo apt-get install docker-ce
  sudo groupadd docker
  sudo usermod -aG docker $USER
  ```
  Log out and log back in so that your group membership is re-evaluated.
- python3-dev
    ```bash
    sudo apt-get install python3-dev
    ```

### Configuration

When running `cwl-airflow init` the following parameters can be specified:

- `-l LIMIT`, `--limit LIMIT` sets the number of processed jobs kept in history.
 Default 10 for each of the category: *Running*, *Success*, *Failed* 
- `-j JOBS`, `--jobs JOBS` sets the path to the folder where all the new jobs will be added.
Default `~/airflow/jobs`
- `-t DAG_TIMEOUT`, `--timeout DAG_TIMEOUT` sets timeout (in seconds) for importing all the DAGs
from the DAG folder. Default 30 seconds 
- `-r WEB_INTERVAL`, `--refresh WEB_INTERVAL` sets the webserver workers refresh interval (in seconds). Default 30 seconds
- `-w WEB_WORKERS`, `--workers WEB_WORKERS` sets the number of webserver workers to be refreshed at the same time. Default 1
- `-p THREADS`, `--threads THREADS` sets the number of threads for Airflow Scheduler. Default 2

If *core/dags_folder* parameters from Airflow configuration file (default location *~/airflow/airflow.cfg*)
has been updated manualy, make sure to rerun `cwl-airflow init`

    
### Running
#### Batch mode
To automatically monitor and process all the job files present in a specific folder
1. Make sure your job files include the following mandatory fields:
   - `uid` - unique ID, string
   - `output_folder` - absolute path the the folder to save result, string
   - `workflow` - absolute path the the workflow to be run, string
    
   Aditionally, job files may also include the `tmp_folder` parameter
   to point to the temporary folder absolute path. 
2. Put your JSON/YAML job files into the directory
   set as `jobs` in `cwl` section of `airflow.cfg` file
   (by default `~/airflow/cwl/jobs`)
3. Run Airflow scheduler:
   ```sh
   $ airflow scheduler
   ```
   
#### Manual mode
To perform a single run of the specific CWL workflow and job files 

```bash
cwl-airflow run WORKFLOW_FILE JOB_FILE
```
If `uid`, `output_folder`, `workflow` and `tmp_folder` fields are not present
in the job file, you may set the them with the following arguments:
```bash
  -o, --outdir      Output directory, default current directory
  -t, --tmp         Folder to store temporary data, default /tmp
  -u, --uid         Unique ID, default random uuid
```
#### Demo mode
1. Get the list of the available demo workflows to run
   ```bash
   $ cwl-airflow demo
   ```
2. Run demo workflow from the list (if running on macOS, consider adding the directory where you
   installed cwl-airflow package to the _**Docker / Preferences / File sharing**_ options)
   ```bash
   $ cwl-airflow demo super-enhancer.cwl
   ```
3. Optionally, run `airflow webserver` to check workflow status (default [webserver link](http://localhost:8080/))
     ```bash
   $ airflow webserver
   ```
   