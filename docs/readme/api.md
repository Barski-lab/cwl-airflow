# API

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

**For detailed API specification, please follow the link on [SwaggerHub](https://app.swaggerhub.com/apis/michael-kotliar/cwl_airflow_workflow_execution_service/1.0.0)**
