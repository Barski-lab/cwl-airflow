#!/bin/bash

echo "Set parameters from the environment variables or apply defaults"
: "${MYSQL_USER:=airflow}"
: "${MYSQL_PASSWORD:=airflow}"
: "${MYSQL_DATABASE:=airflow}"

echo "Wait until required database is ready"
until mysql -h mysql -u ${MYSQL_USER} -p${MYSQL_PASSWORD} -e "USE ${MYSQL_DATABASE}"
do
    echo "Sleep 1 sec"
    sleep 1;
done

echo "Run initial configuration for CWL-Airflow"
cwl-airflow init --upgrade

echo "Start airflow scheduler"
airflow scheduler "$@"
