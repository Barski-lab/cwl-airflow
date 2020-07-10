# Quick start

We assume that you have already installed **python3**, latest **pip**, latest **setuptools**
and **docker** that has access to pull images from the [DockerHub](https://hub.docker.com/).
If something is missing or should be updated refer to the [Installation](./installation.md)
or [Troubleshooting](./troubleshooting.md) sections.

1. Install cwl-airflow
    ```sh
    $ pip install cwl-airflow
    ```

2. Configure cwl-airflow
    ```sh
    $ cwl-airflow init
    ```

3. Get some workflows to run, for example from [SciDAP](https://github.com/datirium/workflows)
    ```sh
    $ git clone https://github.com/datirium/workflows.git --recursive
    ```

4. In a separate terminals start Airflow Webserver, Scheduler and our API
   ```sh
   $ airflow scheduler
   $ airflow webserver
   $ cwl-airflow api
   ```

4. Schedule execution of a sample workflow set with `--range`
    ```sh
    $ cwl-airflow test --suite workflows/tests/conformance_tests.yaml --range 1
    ```

5. Open Airflow Webserver (by default [localhost:8080](http://127.0.0.1:8080/admin/)) and wait until Airflow Scheduler pick up a new DAG (by default every 5 min) and execute it. On completion all results and temporary files will be removed, so you can safely scheduler other workflows by setting different values to `--range` parameter.

![Airflow web interface](../images/screen.png)
