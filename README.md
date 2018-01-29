[![Build Status](https://travis-ci.org/Barski-lab/cwl-airflow.svg?branch=master)](https://travis-ci.org/Barski-lab/cwl-airflow)
# cwl-airflow

### About
Python package to extend **[Apache-Airflow 1.8.2](https://github.com/apache/incubator-airflow)**
functionality with **[CWL v1.0](http://www.commonwl.org/v1.0/)** support.

### Installation
1. Get the latest release of `cwl-airflow`
      ```sh
      $ pip install cwl-airflow
      ```
   
    <details> 
      <summary>Details & Requirements</summary>
      
      Automatically installs:
      - Apache-Airflow v1.8.2 
      - cwltool 1.0.20180116213856
          
      Requirements:
      - Ubuntu 16.04.3
        - python 2.7.12
        - pip
          ```
          wget https://bootstrap.pypa.io/get-pip.py
          python get-pip.py --user
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
    </details>


### Configuration
1. If you had **[Apache-Airflow v1.8.2](https://github.com/apache/incubator-airflow)**
   already installed and configured, you may skip this step
    ```sh
    $ airflow initdb
    ```
    <details> 
        <summary>Details</summary>
    
    - creates `$AIRFLOW_HOME` folder (if not set `~/airflow` is used)
    - creates default Airflow configuration file `airflow.cfg`
      in the `$AIRFLOW_HOME` folder
    - initializes Airflow database
        
    </details>

2. Initialize `cwl-airflow` with the following command
    ```sh
    $ cwl-airflow init
    ```
    
    <details> 
        <summary>Details</summary>
    
    - updates `airflow.cfg` file from `$AIRFLOW_HOME` folder with the new section `[cwl]`
      to set the default parameters for running CWL workflow descriptor files.
      `[AIRFLOW_HOME]` will be replaced by `$AIRFLOW_HOME` value.
      ```bash
      [cwl]
      cwl_workflows = [AIRFLOW_HOME]/cwl/workflows
      cwl_jobs = [AIRFLOW_HOME]/cwl/jobs
      output_folder = [AIRFLOW_HOME]/cwl/output
      tmp_folder = [AIRFLOW_HOME]/cwl/tmp
      max_jobs_to_run = 2
      log_level = ERROR
      strict = False
      ```
    - creates default folders for CWL descriptor and JSON/YAML
      input parameters files based on `cwl` section from `airflow.cfg` file
    - creates `cwl_airflow` folder in the directory set as `dags_folder` parameter
      in `airflow.cfg` file, copies there `cwl_airflow` Python package for generating
      DAG's from CWL files
        
    </details>




### Running


#### Batch mode
1. Put your CWL descriptor files with all of the nested tools and subworkflows
   into the folder set as `cwl_workflows` parameter in `cwl` section
   of `airflow.cfg` file (by default `$AIRFLOW_HOME/cwl/workflows`)

2. Put your JSON/YAML input parameters files into subfolder `new`
   of the directory set as `cwl_jobs` parameter
   in `cwl` section of `airflow.cfg` file
   (by default `$AIRFLOW_HOME/cwl/cwl_jobs/new`)

3. Run Airflow scheduler:
   ```sh
   $ airflow scheduler
   ```
   <details> 
    <summary>Details</summary>
    
    - Loads `cwl_airflow` Python package from `dags_folder` to generate new DAG's
    - Loads JSON/YAML input parameters file from the subfolder `new`
      of the directory set as `cwl_jobs` parameter
      in `cwl` section of `airflow.cfg` file (by default `$AIRFLOW_HOME/cwl/cwl_jobs/new`)
    - Based on loaded JSON/YAML input parameters file name fetches CWL descriptor file
      from the directory set as `cwl_workflows` parameter
      in `cwl` section of `airflow.cfg` file (by default `$AIRFLOW_HOME/cwl/workflows`).
      The following naming rule should be kept
      ```
      [identical].cwl                       - CWL workflow descriptor file name
      [identical][arbitrary].json(yaml)     - JSON/YAML input parameters file name
      ```
    </details>
   
   
#### Manual mode
Use `cwl-airflow` with explicitly specified CWL descriptor
and JSON/YAML input parameters files.

```bash
   cwl-airflow run WORKFLOW_FILE JOB_FILE
```

<details> 
<summary>Details</summary>

- Creates DAG from CWL descriptor and JSON/YAML input parameters files
- Schedule newly created DAG for running

</details>

#### Collecting output
  For both batch and manual modes all of the output files are saved
  into the separate folders. The name of the folder corresponds to
  JSON/YAML input parameters file name. All output folders are created
  in the directory set as `output_folder` parameter in `cwl` section
  of `airflow.cfg` file (by default `$AIRFLOW_HOME/cwl/output`).
  
### Running example workflow
1. Git clone **[ChIP-Seq CWL pipeline](https://github.com/Barski-lab/ga4gh_challenge)**
   repository into the folder set as `cwl_workflows` parameter
   in `cwl` section of `airflow.cfg` file (by default `$AIRFLOW_HOME/cwl/workflows`).
   
   ```bash
   $ git clone --recursive --branch v0.0.2b https://github.com/Barski-lab/ga4gh_challenge.git
   ```
2. Decompress input FASTQ file by running the script from the `data` directory of
   repository clonned in the previous step. If all settings are set by default the
   location of the script will be `$AIRFLOW_HOME/cwl/workflows/ga4gh_challenge/data`
      
   ```sh
   $ ./prepare_inputs.sh
   ```
   <details> 
     <summary>Details</summary>
    
     - Decompress and combine all of the files in `./inputs`
       directory into `SRR1198790.fastq` file
    </details>
   
   
3. Create input parameters file `biowardrobe_chipseq_se.yaml` in the subfolder `new`
   of the directory set as `cwl_jobs` parameter in `cwl` section of `airflow.cfg` file
   (by default `$AIRFLOW_HOME/cwl/cwl_jobs/new`).
   In the text below replace `[cwl_workflows]` with the folder set as `cwl_workflows` parameter
   in `cwl` section of `airflow.cfg` file (by default `$AIRFLOW_HOME/cwl/workflows`).
   
   ```yaml
    fastq_file:
      class: File
      location: "[cwl_workflows]/ga4gh_challenge/data/inputs/SRR1198790.fastq"
      format: "http://edamontology.org/format_1930"
    indices_folder:
      class: Directory
      location: "[cwl_workflows]/ga4gh_challenge/data/references/dm3/bowtie_indices"
    annotation_file:
      class: File
      location: "[cwl_workflows]/ga4gh_challenge/data/references/dm3/refgene.tsv"
      format: "http://edamontology.org/format_3475"
    chrom_length:
      class: File
      location: "[cwl_workflows]/ga4gh_challenge/data/references/dm3/chrNameLength.txt"
      format: "http://edamontology.org/format_2330"
    clip_3p_end: 0
    clip_5p_end: 0
    remove_duplicates: false
    exp_fragment_size: 150
    force_fragment_size: false
    broad_peak: false
    threads: 8
    genome_size: "1.2e8"
    ```
4. Pull all necessary Docker images
    ```bash
    docker pull biowardrobe2/samtools:v1.4
    docker pull biowardrobe2/scidap:v0.0.2
    docker pull biowardrobe2/iaintersect:v0.0.2
    docker pull biowardrobe2/bowtie:v1.2.0
    docker pull biowardrobe2/bedtools2:v2.26.0
    docker pull biowardrobe2/macs2:v2.1.1
    docker pull biowardrobe2/atdp:v0.0.1
    docker pull biowardrobe2/ucscuserapps:v358
    docker pull biowardrobe2/fastx_toolkit:v0.0.14
    ```
5. Start airflow scheduler
   ```bash
    airflow scheduler
   ```
6. To check the status of running DAG start Airflow Webserver
   and open its URL link in a web browser
   (by default **[http://localhost:8080](http://localhost:8080/)**)
   ```bash
   airflow webserver
   ```
   When the DAG is finished, output files will be saved into subfolder
   of the directory set as `output_folder` parameter in `cwl` section
   of `airflow.cfg` file (by default `$AIRFLOW_HOME/cwl/output`).