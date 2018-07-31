[![Build Status](https://travis-ci.org/Barski-lab/cwl-airflow.svg?branch=master)](https://travis-ci.org/Barski-lab/cwl-airflow) -  **Travis CI**  
[![Build Status](https://ci.commonwl.org/buildStatus/icon?job=airflow-conformance)](https://ci.commonwl.org/job/airflow-conformance) - **CWL conformance tests**  

# cwl-airflow

Python package to extend **[Apache-Airflow 1.9.0](https://github.com/apache/incubator-airflow)**
functionality with **[CWL v1.0](http://www.commonwl.org/v1.0/)** support.
_________________
### Quick guides
1. Install *cwl-airflow*
    ```sh
    $ pip install cwl-airflow --user --find-links https://michael-kotliar.github.io/cwl-airflow-wheels/
    ```
2. Init configuration
    ```sh
    $ cwl-airflow init
    ```
3. Run *demo*
    ```sh
    $ cwl-airflow demo --auto
    ```
4. When you see in the console output that Airflow Webserver is started,
open the provided URL address 

_________________

### Installation requirements
#### OS specific
##### Ubuntu 16.04.4
- python 2.7/3.5 (tested on the system Python 2.7.12 and the latest available 3.5.2)
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
- python-dev (or python3-dev if using Python 3.5)
  ```bash
  sudo apt-get install python-dev # python3-dev
  ``` 
##### macOS High Sierra 10.13.5
- python 2.7/3.6 (tested on the system Python 2.7.10 and the latest availble 3.6.5)
- docker (follow the official [install](https://docs.docker.com/docker-for-mac/install/) documentation)
  
#### Common 
- pip
  ```bash
  wget https://bootstrap.pypa.io/get-pip.py
  python get-pip.py --user
  ```
  When using the system Python, you might need to update your PATH variable following
  the instruction printed on console
- setuptools
  ```
  pip install -U setuptools --user
  ```
- Apple Command Line Tools
  ```bash
  xcode-select --install
  ```
  Click Install on the pop up when it appears.

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

If you update Airflow configuration file (default location *~/airflow/airflow.cfg*) manually,
make sure to run *cwl-airflow init* command to apply all the changes,
especially if *core/dags_folder* or *cwl/jobs* parameters are changed.

    
### Submitting a job
To submit new cwl workflow descriptor and input parameters file for execution it's recommended to use
 *cwl-airflow submit* command.
   
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
   