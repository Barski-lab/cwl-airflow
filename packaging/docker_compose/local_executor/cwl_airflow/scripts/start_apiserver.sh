#!/bin/bash

echo "Set parameters from the environment variables or apply defaults"
: ${MYSQL_USER:=airflow}
: ${MYSQL_PASSWORD:=airflow}
: ${MYSQL_DATABASE:=airflow}

echo "Wait until required database and tables are ready"
until mysql -h mysql -u ${MYSQL_USER} -p${MYSQL_PASSWORD} -e "select * from ${MYSQL_DATABASE}.dag_run"
do
    echo "Sleep 1 sec"
    sleep 1;
done

echo "Start cwl-airflow api"
cwl-airflow api "$@"