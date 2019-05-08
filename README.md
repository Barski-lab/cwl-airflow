[![DOI](https://zenodo.org/badge/103197335.svg)](https://zenodo.org/badge/latestdoi/103197335)
[![Python 2.7](https://img.shields.io/badge/python-2.7-green.svg)](https://www.python.org/downloads/release/python-2712/)
[![Python 3.5](https://img.shields.io/badge/python-3.5-green.svg)](https://www.python.org/downloads/release/python-352/)
[![Python 3.6](https://img.shields.io/badge/python-3.6-green.svg)](https://www.python.org/downloads/release/python-365/)

[![Build Status](https://travis-ci.org/Barski-lab/cwl-airflow.svg?branch=master)](https://travis-ci.org/Barski-lab/cwl-airflow) -  **Travis CI**  
[![Build Status](https://ci.commonwl.org/buildStatus/icon?job=airflow-conformance)](https://ci.commonwl.org/job/airflow-conformance) - **CWL conformance tests**



# cwl-airflow

Python package to extend **[Apache-Airflow 1.9.0](https://github.com/apache/incubator-airflow)**
functionality with **[CWL v1.0](http://www.commonwl.org/v1.0/)** support.

## Table of Contents
* **[Run demo](#run-demo)**
  * [Locally](#locally)
  * [VirtualBox](#virtualbox)
* **[How It Works](#how-it-works)**
  * [Key concepts](#key-concepts)
  * [What's inside](#whats-inside)
* **[Installation](#installation)**
  * [Requirements](#requirements)
    * [Ubuntu 16.04.4 (Xenial Xerus)](#ubuntu-16044-xenial-xerus)
    * [macOS 10.13.5 (High Sierra)](#macos-10135-high-sierra)
    * [Both Ubuntu and macOS](#both-ubuntu-and-macos)
  * [Install cwl-airflow](#install-cwl-airflow)
* **[Using cwl-airflow](#using-cwl-airflow)**
    * [Configuration](#configuration)
    * [Submitting new job](#submitting-new-job)
    * [Demo mode](#demo-mode)
    * [Running sample ChIP-Seq-SE workflow](#running-sample-chip-seq-se-workflow)
* **[Troubleshooting](#troubleshooting)**
* **[Citation](#citation)**
* **[License](#license)**

---

## Run demo

### Locally

We assume that you have already installed and properly configured **python**, latest **pip**, latest **setuptools**
and **docker** that has access to pull images from the [DockerHub](https://hub.docker.com/). If something is missing or should be updated refer to the [Installation](#installation) or [Troubleshooting](#troubleshooting) sections

1. Install *cwl-airflow*
    ```sh
    $ pip install cwl-airflow --find-links https://michael-kotliar.github.io/cwl-airflow-wheels/ # --user
    ```
    `--user` - explained [here](#both-ubuntu-and-macos)

2. Init configuration
    ```sh
    $ cwl-airflow init
    ```

3. Run *demo*
    ```sh
    $ cwl-airflow demo --auto
    ```

4. When all demo wokrflows are submitted the program will provide you with the link for Airflow Webserver (by default it is accessible from your [localhost:8080](http://127.0.0.1:8080/admin/)).
It may take some time (usually less then half a minute) for Airflow Webserver to load and display all the data

![Airflow Webserver example](https://raw.githubusercontent.com/Barski-lab/cwl-airflow/master/docs/screen.png)

5. On completion the workflow results will be saved in the current folder

### VirtualBox
In order to run CWL-Airflow virtual machine you have to install [Vagrant](https://www.vagrantup.com/downloads.html) and [VirtualBox](https://www.virtualbox.org/wiki/Downloads). The host machine should have access to the Internet, at least 8 CPUs and 16 GB of RAM.

1. Clone CWL-Airflow repository
    ```bash
    $ git clone https://github.com/Barski-lab/cwl-airflow
    ```

2. Chose one of three possible configurations to run

   **Single node**
   ```bash
   $ cd ./cwl-airflow/vagrant/local_executor
   ```
   **Celery Cluster of 3 nodes (default queue)**
   ```bash
   $ cd ./cwl-airflow/vagrant/celery_executor/default_queue
   ```
   **Celery Cluster of 4 nodes (default + advanced queues)**
   ```bash
   $ cd ./cwl-airflow/vagrant/celery_executor/custom_queue
   ```

3. Start virtual machine
    ```bash
    $ vagrant up
    ```
    Vagrant will pull the latest virtual machine image (about 3.57 GB) from [Vagrant Cloud](https://app.vagrantup.com/michael_kotliar/boxes/cwl-airflow). When started the following folders will be created on the host machine in the current directory.
    ```bash
    ├── .vagrant
    └── airflow
        ├── dags
        │   └── cwl_dag.py      # creates DAGs from CWLs
        ├── demo
        │   ├── cwl
        │   │   ├── subworkflows
        │   │   ├── tools
        │   │   └── workflows   # demo workflows
        │   │       ├── chipseq-se.cwl
        │   │       ├── super-enhancer.cwl
        │   │       └── xenbase-rnaseq-se.cwl
        │   ├── data            # input data for demo workflows
        │   └── job             # sample job files for demo workflows
        │       ├── chipseq-se.json
        │       ├── super-enhancer.json
        │       └── xenbase-rnaseq-se.json
        ├── jobs                # folder for submitted job files
        ├── results             # folder for workflow outputs
        └── temp                # folder for temporary data

    ```

4. Connect to running virtual machine through `ssh`
    ```sh
    $ vagrant ssh master
    ```

5. Submit all demo workflows for execution
    ```sh
    $ cd airflow/results
    $ cwl-airflow demo --manual
    ```

6. Open Airflow Webserver ([localhost:8080](http://127.0.0.1:8080/admin/)) and, if multi-node configuration is run, Celery Flower Monitoring Tool ([localhost:5555](http://127.0.0.1:5555)). It might take up to 20 seconds for Airflow Webserver to display all newly added workflows.

7. On completion, view workflow execution results in the `./airflow/results` folder on your host machine.

8. Stop `ssh` connection to the virtual machine by pressing  `ctlr+D` and then run one of the following commands
   ```sh
   $ vagrant halt    # stop virtial machines
   ```
   or
   ```bash
   $ vagrant destroy            # remove virtual machines
   $ rm -rf ./airflow .vagrant  # remove created folders
   ``` 
---

## How It Works
### Key concepts

1. **CWL descriptor file** - *YAML* or *JSON* file to describe the workflow inputs, outputs and steps.
   File should be compatible with CWL v1.0 specification
2. **Job file** - *YAML* or *JSON* file to set the values for the wokrflow inputs.
   For *cwl-airflow* to function properly the Job file should include 3 mandatory and 
   one optional fields:
   - *workflow* - mandatory field to specify the absolute path to the CWL descriptor file
   - *output_folder* - mandatory field to specify the absolute path to the folder
   where all the output files should be moved after successful workflow execution
   - *tmp_folder* - optional field to specify the absolute path to the folder
   for storing intermediate results. After workflow execution this folder will be deleted.
   - *uid* - mandatory field that is used for generating DAG's unique identifier. 
3. **DAG** - directed acyclic graph that describes the workflow structure.
4. **Jobs folder** - folder to keep all Job files scheduled for execution or the ones that
have already been processed. The folder's location is set as *jobs* parameter of *cwl* section
in Airflow configuration file.  

### What's inside
To build a workflow *cwl-airflow* uses three basic classes:
- *CWLStepOperator* - executes a separate workflow step 
- *JobDispatcher* - serializes the Job file and provides the worflow with input data
- *JobCleanup* - returns the calculated results to the output folder

A set of *CWLStepOperator*s, *JobDispatcher* and *JobCleanup* are
combined in *CWLDAG* that defines a graph to reflect the workflow steps, their relationships
and dependencies. Automatically generated *cwl_dag.py* script is placed in the DAGs folder. When Airflow
Scheduler loads DAGs from the DAGs folder, the *cwl_dag.py* script parses all the Job files from the Jobs folder
and creates DAGs for each of them. Each DAG has a unique DAG ID that is formed accodring to the following scheme:
`CWL descriptor file basename`-`Job file basename`-`uid field from the Job file`

![Airflow Webserver example](https://raw.githubusercontent.com/Barski-lab/cwl-airflow/master/docs/scheme.png)

---

## Installation
### Requirements 
#### Ubuntu 16.04.4 (Xenial Xerus)
- python 2.7 or 3.5 (tested on the system Python 2.7.12 and 3.5.2)
- docker (follow the [link](https://docs.docker.com/install/linux/docker-ce/ubuntu/) to install Docker on Ubuntu)
  
  **Don't forget** to add your user to the *docker* group and then
  to log out and log back in so that your group membership is re-evaluated.
- python-dev (or python3-dev if using Python 3.5)
  ```bash
  sudo apt-get install python-dev # python3-dev
  ``` 
  *python-dev* is required in case your system needs to compile some python
  packages during the installation. We have built python *wheels* for most of such packages
  and provided them through *--find-links* argument while installing *cwl-airflow*.
  Nevertheless in case of installation problems you might still be required to install
  this dependency.
  
#### macOS 10.13.5 (High Sierra)
- python 2.7 or 3.6 (tested on the system Python 2.7.10 and brewed Python 2.7.15 / 3.6.5; **3.7.0 is not supported**)
- docker (follow the [link](https://docs.docker.com/docker-for-mac/install/) to install Docker on Mac)
- Apple Command Line Tools
  ```bash
  xcode-select --install
  ```
  Click *Install* on the pop up when it appears, follow the instructions. *Apple Command Line Tools* are required in
  case your system needs to compile some python packages during the installation. We have built python wheels for most
  of such packages and provided them through *--find-links* argument while installing *cwl-airflow*. Nevertheless in case
  of installation problems you might still be required to install this dependency.
  
#### Both Ubuntu and macOS
- pip (follow the [link](https://pip.pypa.io/en/stable/installing/) to install the latest stable Pip)

  Consider using `--user` if you encounter permission problems 
  
- setuptools (tested on setuptools 40.0.0)
  ```bash
  pip install -U setuptools # --user
  ```
  
  `--user` - optional parameter to install all the packages into your *HOME* directory instead of the system Python
  directories. It will be helpful if you don't have enough permissions to install new Python packages.
  You might also need to update your *PATH* variable in order to have access to the installed packages (an easy
  way to do it is described in [Troubleshooting](#troubleshooting) section).
  If installing on macOS brewed Python `--user` **should not** be used (explained [here](https://docs.brew.sh/Homebrew-and-Python))

### Install cwl-airflow
```sh
$ pip install cwl-airflow --find-links https://michael-kotliar.github.io/cwl-airflow-wheels/ # --user
```
`--find-links` - using pre-compiled wheels from [This](https://michael-kotliar.github.io/cwl-airflow-wheels/) repository
allows to avoid installing *Xcode* for macOS users and *python[3]-dev* for Ubuntu users

  `--user` - explained [here](#both-ubuntu-and-macos)

---

## Using cwl-airflow

### Configuration

Before using *cwl-airflow* it should be initialized with the default configuration by running the command
```sh
$ cwl-airflow init
```

Optional parameters:

| Flag | Description                                                           | Default                                       |
|------|-----------------------------------------------------------------------|-----------------------------------------------|
| -l   | number of processed jobs kept in history, int                         | 10 x *Running*, 10 x *Success*, 10 x *Failed* |
| -j   | path to the folder where all the new jobs will be added, str          | *~/airflow/jobs*                              |
| -t   | timeout for importing all the DAGs from the DAG folder, sec           | 30                                            |
| -r   | webserver workers refresh interval, sec                               | 30                                            |
| -w   | number of webserver workers to be refreshed at the same time, int     | 1                                             |
| -p   | number of threads for Airflow Scheduler, int                          | 2                                             |

Consider using `-r 5 -w 4` to make Airflow Webserver react faster on all newly created DAGs

If you update Airflow configuration file manually (default location is *~/airflow/airflow.cfg*),
make sure to run *cwl-airflow init* command to apply all the changes,
especially if *core/dags_folder* or *cwl/jobs* parameters from the configuration file are changed.
  
### Submitting new job

To submit new CWL descriptor and Job files to *cwl-airflow* run the following command
```bash
cwl-airflow submit WORKFLOW JOB
```

Optional parameters:

| Flag | Description                                                                                            | Default           |
|------|--------------------------------------------------------------------------------------------------------|-------------------|
| -o   | path to the folder where all the output files should be moved after successful workflow execution, str | current directory |
| -t   | path to the temporary folder for storing intermediate results, str                                     | */tmp/cwlairflow* |
| -u   | ID for DAG's unique identifier generation, str                                                         | random uuid       |
| -r   | run submitted workflow with Airflow Scheduler, bool                                                    | False             |

Arguments `-o`, `-t` and `-u` doesn't overwrite the values from the Job file set in the fields
*output_folder*, *tmp_folder* and *uid* correspondingly. The meaning of these fields is explaned in
[Key concepts](#key-concepts) section.

The *submit* command will resolve all relative paths from Job file adding mandatory fields *workflow*, *output_folder*
and *uid* (if not provided) and will copy Job file to the Jobs folder. The CWL descriptor file and all input files
referenced in the Job file should not be moved or deleted while workflow is running. The *submit* command will **not** execute
submitted workflow unless *-r* argument is provided. Otherwise, make sure that *Airflow Scheduler* (and optionally
*Airflow Webserver*) is running. Note, that *-r* argument was added only to comply with the interface through which CWL
community runs it's conformance tests. So it's more preferable to execute submitted workflow with
*Airflow Scheduler*, especially if you are planning to use `LocalExecutor` instead of default `SequentialExecutor` (refer to [Airflow
documentation](http://airflow.apache.org/code.html?highlight=sequentialexecutor#executors) to chose proper executor)

Depending on your Airflow configuration it may require some time for Airflow Scheduler
and Webserver to pick up new DAGs. Consider using `cwl-airflow init -r 5 -w 4` to make Airflow Webserver react faster on all
newly created DAGs.  

To start Airflow Scheduler (**don't** run it if *cwl-airflow submit* is used with *-r* argument)
```bash
airflow scheduler
```
To start Airflow Webserver (by default it is accessible from your [localhost:8080](http://127.0.0.1:8080/admin/))
```bash
airflow webserver
```

Please note that both Airflow Scheduler and Webserver can be adjusted through the configuration file
(default location is *~/airflow/airflow.cfg*). Refer to the official documentation [here](https://airflow.apache.org/configuration.html) 
 
### Demo mode
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
    Before submitting and running demo workflows the Jobs folder will be automatically cleaned.
    
Optional parameters:

| Flag | Description                                                                                            | Default           |
|------|--------------------------------------------------------------------------------------------------------|-------------------|
| -o   | path to the folder where all the output files should be moved after successful workflow execution, str | current directory |
| -t   | path to the temporary folder for storing intermediate results, str                                     | */tmp/cwlairflow* |
| -u   | ID for DAG's unique identifier generation, str. Ignored when *--list* or *--auto* is used              | random uuid       |

### Running sample ChIP-Seq-SE workflow
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
$ git clone --recursive https://github.com/Barski-lab/ga4gh_challenge.git --branch v0.0.3
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
To start Airflow Webserver (by default it is accessible from your [localhost:8080](http://127.0.0.1:8080/admin/))
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


### Troubleshooting

Most of the problems are already handled by *cwl-airflow* itself. User is provided
with the full explanation and ways to correct them through the console output. Additional
information regarding the failed workflow steps, can be found in the task execution logs
that are accessible through Airflow Webserver UI. 

Common errors and ways to fix them
- ***`cwl-airflow` is not found*** 
   
   Perhaps, you have installed it with *--user* option and your *PATH*
   variable doesn't include your user based Python *bin* folder.
   Update *PATH* with the following command
   ```sh
   export PATH="$PATH:`python -m site --user-base`/bin"
   ```
- ***Fails to install on the latest Python 3.7.0***
  
  Unfortunatelly *Apache-Airflow 1.9.0* cannot be properly installed on the latest *Python 3.7.0*.
  Consider using *Python 3.6* or *2.7* instead.
  
  macOS users can install Python 3.6.5 (instead of the latest Python 3.7.0) with the following command
  (explained [here](https://stackoverflow.com/a/51125014/8808721))
  ```bash
    brew install https://raw.githubusercontent.com/Homebrew/homebrew-core/f2a764ef944b1080be64bd88dca9a1d80130c558/Formula/python.rb
  ```

- ***Fails to compile ruamel.yaml***
   
  Perhaps, you should update your *setuptools*. Consider using *--user* if necessary.
  If installing on macOS brewed Python *--user* **should not** be used (explained [here](https://docs.brew.sh/Homebrew-and-Python))
  ```bash
  pip install -U setuptools # --user
  ```
  `--user` - explained [here](#both-ubuntu-and-macos)
  
- ***Docker is unable to pull images from the Internet***

  If you are using proxy, your Docker should be configured properly too.
  Refer to the official [documentation](https://docs.docker.com/config/daemon/systemd/#httphttps-proxy)
   
- ***Docker is unable to mount directory***

  For macOS docker has a list of directories that it's allowed to mount by default. If your input files are located in
  the directories that are not included in this list, you are better of either changing the location of
  input files and updating your Job file or adding this directories into Docker configuration *Preferences / File Sharing*.

- ***Airflow Webserver displays missing DAGs***

  If some of the Job files have been manually deleted, they will be still present in Airflow database, hence they 
  will be displayed in Webserver's UI. Sometimes you may still see missing DAGs because of the inertness of Airflow
  Webserver UI.

- ***Airflow Webserver randomly fails to display some of the pages***

  When new DAG is added Airflow Webserver and Scheduler require some time to update their states.
  Consider using `cwl-airflow init -r 5 -w 4` to make Airflow Webserver react faster for all newly created DAGs.
  Or manualy update Airflow configuration file (default location is *~/airflow/airflow.cfg*) and restart both
  Webserver and Scheduler. Refer to the official documentation [here](https://airflow.apache.org/configuration.html) 
  
- ***Workflow execution fails***

  Make sure that CWL descriptor and Job files are correct. You can always check them with *cwltool*
  (trusted version 1.0.20180622214234)
  ```bash
  cwltool --debug WORKFLOW JOB
  ```

 
### Citation

*[CWL-Airflow: a lightweight pipeline manager supporting Common Workflow Language](https://www.biorxiv.org/content/early/2018/01/17/249243)*

### License

[Apache License Version 2.0](https://www.apache.org/licenses/LICENSE-2.0)