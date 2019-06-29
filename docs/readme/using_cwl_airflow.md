# Using cwl-airflow

## Configuration

Before using *cwl-airflow* it should be initialized with the default configuration by running the command
```sh
$ cwl-airflow init
```

Optional parameters:

| Flag | Description                                                        | Default           |
|------|--------------------------------------------------------------------|-------------------|
| -l   | number of processed jobs kept in history, int                      | 10 x *Running*    |
|      |                                                                    | 10 x *Success*    |
|      |                                                                    | 10 x *Failed*     |
| -j   | path to the folder where all the new jobs will be added, str       | *~/airflow/jobs*  |
| -t   | timeout for importing all the DAGs from the DAG folder, sec        | 30                |
| -r   | webserver workers refresh interval, sec                            | 30                |
| -w   | number of webserver workers to be refreshed at the same time, int  | 1                 |
| -p   | number of threads for Airflow Scheduler, int                       | 2                 |

Consider using `-r 5 -w 4` to make Airflow Webserver react faster on all newly created DAGs

If you update Airflow configuration file manually (default location is *~/airflow/airflow.cfg*),
make sure to run *cwl-airflow init* command to apply all the changes,
especially if *core/dags_folder* or *cwl/jobs* parameters from the configuration file are changed.
  
## Submitting new job

To submit new CWL descriptor and Job files to *cwl-airflow* run the following command
```bash
cwl-airflow submit WORKFLOW JOB
```

Optional parameters:

| Flag | Description                                                        | Default           |
|------|--------------------------------------------------------------------|-------------------|
| -o   | path to the folder where all the output files                      | current directory |
|      | should be moved after successful workflow execution, str           |                   |
| -t   | path to the temporary folder for storing intermediate results, str | */tmp/cwlairflow* |
| -u   | ID for DAG's unique identifier generation, str                     | random uuid       |
| -r   | run submitted workflow with Airflow Scheduler, bool                | False             |

Arguments `-o`, `-t` and `-u` doesn't overwrite the values from the Job file set in the fields
*output_folder*, *tmp_folder* and *uid* correspondingly. The meaning of these fields is explaned in
[How It Works](./how_it_works.md) section.

The *submit* command will resolve all relative paths from Job file adding mandatory fields *workflow*, *output_folder*
and *uid* (if not provided) and will copy Job file to the Jobs folder. The CWL descriptor file and all input files
referenced in the Job file should not be moved or deleted while workflow is running. The *submit* command will **not** execute
submitted workflow unless *-r* argument is provided. Otherwise, make sure that *Airflow Scheduler* (and optionally
*Airflow Webserver*) is running. Note, that *-r* argument was added only to comply with the interface through which CWL
community runs it's conformance tests. So it's more preferable to execute submitted workflow with
*Airflow Scheduler*, especially if you are planning to use `LocalExecutor` instead of default `SequentialExecutor`.

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
