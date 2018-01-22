# cwl-airflow

### About
Python package to extend **[Apache-Airflow 1.8.2](https://github.com/apache/incubator-airflow)**
functionality with **[CWL v1.0](http://www.commonwl.org/v1.0/)** support.

TODO:
Update json file when we copy it to jobs/new to point to correct input file location


### Installation
1. Make sure your system satisfies the following criteria:
      - Ubuntu 16.04.3
        - python 2.7.12
        - pip
          ```
          sudo apt install python-pip
          pip install --upgrade pip
          ```
        - setuptools
          ```
          pip install setuptools
          ```
        - [docker](https://docs.docker.com/engine/installation/linux/docker-ce/ubuntu/)
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
        - libmysqlclient-dev
          ```bash
          sudo apt-get install libmysqlclient-dev
          ```
        - nodejs
          ```
          sudo apt-get install nodejs
          ```
2. Get the latest version of `cwl-airflow`.
   If you don't want to download workflow example and its input data,
   omit `--recursive` flag). If **[Apache-Airflow](https://github.com/apache/incubator-airflow)**
   or **[cwltool](http://www.commonwl.org/ "cwltool main page")** aren't installed,
   it will be done automatically with recommended versions:
   **Apache-Airflow v1.8.2**, **cwltool 1.0.20180116213856**. If you have already installed
   **Apache-Airflow v1.8.2**, set `AIRFLOW_HOME` environmental variable to point to Airflow
   home directory, before running the following commands.
      ```sh
      $ git clone --recursive https://github.com/Barski-lab/cwl-airflow.git
      $ cd cwl-airflow
      $ pip install --user .
      $ ./post_install.sh
      ```

3. If required, add **[extra packages](https://airflow.incubator.apache.org/installation.html#extra-packages)**
   for extending Airflow functionality with MySQL, PostgreSQL backend support etc.

### Running

#### Automatic mode
1. Put your cwl descriptor file with all of the related tools and subworkflows
   into the folder set as **cwl_workflows** parameter in the **[cwl]** section  of Airflow
   configuration file **airflow.cfg**

2. Put your input parameters file into subfolder **new** of the directory set as **cwl_jobs** parameter
   in the **[cwl]** section  of Airflow configuration file **airflow.cfg**

    - to allow automatically fetch CWL descriptor file by job's file name, follow naming rule
      ```
      [identical].cwl                 - workflow descriptor filename
      [identical][arbitrary].json     - input parameters filename
      ```
      where `[identical]` part of the name defines the correspondence between workflow and job files.
      
    - job file may include additional fields which in case of **output_folder** and **tmp_folder**
      redefines parameters of the same name from **[cwl]** section  of Airflow configuration file
      **airflow.cfg**
      ```     
      {
          "uid": "arbitrary unique id, which will be used for current workflow run",
          "output_folder": "path to the folder to save results",
          "tmp_folder": "path to the folder to save temporary calculation results",
          "author": "Author of a the experiment. Default: CWL-Airflow"
      }
      ```
      
3. Run Airflow scheduler:
   ```sh
   $ airflow scheduler
   ```

#### Manual mode
Use `cwl-airflow-runner` with explicitly specified cwl descriptor `WORKFLOW`
and input parameters `JOB` files.

```bash
   cwl-airflow-runner WORKFLOW JOB
```

If necessary, set additional arguments following the `cwl-airflow-runner --help`


### Collecting output
  All output files will be saved into subfolder of the directory set as **output_folder** parameter
  in the **[cwl]** section of Airflow configuration file **airflow.cfg** with the name corresponding
  to the job file name.
  
### Running example workflow
If you cloned from **[cwl-airflow](https://github.com/Barski-lab/cwl-airflow.git)**
using `--recursive` flag, you may run `cwl-airflow` with example
**[biowardrobe_chipseq_se.cwl](https://github.com/Barski-lab/ga4gh_challenge/blob/master/biowardrobe_chipseq_se.cwl)** workflow.
We assume that you cloned **[cwl-airflow](https://github.com/Barski-lab/cwl-airflow.git)** into `/tmp`,
and **[cwl]** section of your Airflow configuration file **airflow.cfg** has the following values for **cwl_jobs**
and **cwl_workflows** parameters
   - `cwl_jobs = /home/user/airflow/cwl/jobs`
   - `cwl_workflows = /home/user/airflow/cwl/workflows`
   
To run the **[biowardrobe_chipseq_se.cwl](https://github.com/Barski-lab/ga4gh_challenge/blob/master/biowardrobe_chipseq_se.cwl)** workflow
do the following steps:
1. Decompress input FASTQ file, running the script
      
  ```sh
  $ cd /tmp/cwl-airflow/workflow_example/data
  $ ./prepare_inputs.sh
  ```
2. Move `workflow_example` folder into the directory set as **cwl_workflows** parameter in the **[cwl]** section  of Airflow
   configuration file **airflow.cfg**
   
   ```python
   mv /tmp/cwl-airflow/workflow_example /home/user/airflow/cwl/workflows
   ```
   
3. Update input parameters file `biowardrobe_chipseq_se.json`
   with the correct locations of your input files
   ```python
    cat /home/user/airflow/cwl/workflows/workflow_example/biowardrobe_chipseq_se.json
    {
      "fastq_file": {"class": "File", "location": "/home/user/airflow/cwl/workflows/workflow_example/data/inputs/SRR1198790.fastq", "format": "http://edamontology.org/format_1930"},
      "indices_folder": {"class": "Directory", "location": "/home/user/airflow/cwl/workflows/workflow_example/data/references/dm3/bowtie_indices"},
      "annotation_file": {"class": "File", "location": "/home/user/airflow/cwl/workflows/workflow_example/data/references/dm3/refgene.tsv", "format": "http://edamontology.org/format_3475"},
      "chrom_length": {"class": "File", "location": "/home/user/airflow/cwl/workflows/workflow_example/data/references/dm3/chrNameLength.txt", "format": "http://edamontology.org/format_2330"},
      "clip_3p_end": 0,
      "clip_5p_end": 0,
      "remove_duplicates": false,
      "exp_fragment_size": 150,
      "force_fragment_size": false,
      "broad_peak": false,
      "threads": 8,
      "genome_size": "1.2e8"
    }
    ```
4. Move input parameters file `/home/user/airflow/cwl/workflows/workflow_example/biowardrobe_chipseq_se.json`
   into the subfolder **new** of the directory set as **cwl_jobs** parameter in the **[cwl]** section  of Airflow
   configuration file **airflow.cfg**
   ```python
    mv /home/user/airflow/cwl/workflows/workflow_example/biowardrobe_chipseq_se.json /home/user/airflow/cwl/jobs/new 
   ```
5. Start airflow scheduler
   ```python
    airflow scheduler
   ```
