#!/bin/bash

echo "Set parameters from the environment variables or apply defaults"
: ${AIRFLOW_HOME:=airflow}
: ${MYSQL_USER:=airflow}
: ${MYSQL_PASSWORD:=airflow}
: ${MYSQL_DATABASE:=airflow}

echo "Wait until required database and tables are ready"
until mysql -h mysql -u ${MYSQL_USER} -p${MYSQL_PASSWORD} -e "select * from ${MYSQL_DATABASE}.dag_run"
do
    echo "Sleep 1 sec"
    sleep 1;
done

echo "Wait until required files are ready"
until [ -e ${AIRFLOW_HOME}/webserver_config.py ]
do
    echo "Sleep 1 sec"
    sleep 1;
done

echo "Disable authentication in Airflow UI"
sed -i'.backup' -e 's/^# AUTH_ROLE_PUBLIC.*/AUTH_ROLE_PUBLIC = "Admin"/g' ${AIRFLOW_HOME}/webserver_config.py

echo "Start airflow webserver"
airflow webserver "$@"