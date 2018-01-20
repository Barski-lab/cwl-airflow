#!/usr/bin/env bash

HOME_DIR=${AIRFLOW_HOME:-~/airflow}
CONFIG_FILE=$HOME_DIR/airflow.cfg
DAGS=$(grep 'dags_folder' $CONFIG_FILE | awk '{print $NF}')

CWL=$HOME_DIR/cwl
JOBS=$CWL/jobs
WORKFLOWS=$CWL/workflows
TMP=$CWL/tmp
OUTPUT=$CWL/output


echo "Configuration"
echo "  HOME_DIR = $HOME_DIR"
echo "  CONFIG_FILE = $CONFIG_FILE"
echo "  DAGS = $DAGS"

echo "Init Airlow DB"
airflow initdb

echo "Create directories"
echo "  $JOBS/fail"
echo "  $JOBS/new"
echo "  $JOBS/running"
echo "  $JOBS/success"
echo "  $WORKFLOWS"
echo "  $OUTPUT"
echo "  $TMP"

mkdir -p $JOBS/fail $JOBS/new $JOBS/running $JOBS/success $OUTPUT $TMP $WORKFLOWS

echo "Copy cwl_dag.zip to $DAGS"
cd cwl_runner
zip -r cwl_dag.zip ./* -x ./main.py ./*.pyc
mv cwl_dag.zip $DAGS

echo "Set dags_are_paused_at_creation = False in airflow.cfg"
sed "s/.*dags_are_paused_at_creation.*/dags_are_paused_at_creation = False/" $CONFIG_FILE > tempfile; mv tempfile $CONFIG_FILE

echo "Set load_examples = False in airflow.cfg"
sed "s/.*load_examples.*/load_examples = False/" $CONFIG_FILE > tempfile; mv tempfile $CONFIG_FILE

echo "Add [cwl] section to $CONFIG_FILE"
if ! grep -q '\[cwl\]' $CONFIG_FILE; then
cat >> $CONFIG_FILE << EOL
[cwl]
# Absolute path to the folder with job files. Required!
cwl_jobs = $JOBS
# Absolute path to the folder with workflow files. Required!
cwl_workflows = $WORKFLOWS
# Absolute path to the folder to save results. Required!
output_folder = $OUTPUT
# Absolute path to the folder to save temporary calculation results. Default: unique temporary directory in /tmp folder
tmp_folder = $TMP
# Maximum number of jobs to be processed at the same time, int. Default: 1
max_jobs_to_run = 10
# Log level, [CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET]. Default:  INFO
log_level = DEBUG
# enable strict validation, boolean. Default: False
strict = False
EOL
else
echo "[cwl] section is already present in $CONFIG_FILE"
fi
