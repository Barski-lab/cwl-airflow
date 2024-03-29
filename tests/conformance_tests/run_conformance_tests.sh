#!/bin/bash


# Tool runs conformance tests from the provided repository's URL
# and path to the conformance.yaml file using docker-compose.
# All temporary data is kept in the ./temp folder which is cleaned
# before running the tests. If this script was stopped with Ctrl+C,
# docker containers started by docker-compose may still keep running.
# Use `docker-compose -f FILE down` command to stop them. Tests report
# is saved in /temp/tests.log


DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

UBUNTU_VERSION=$1
PYTHON_VERSION=$2
CWL_AIRFLOW_VERSION=$3
REPO_URL=$4
SUITE=$5
PARAMS=${@:6}

if [ $# -lt 2 ]; then
    echo "Usage: run_conformance_tests.sh https://github.com/repository.git ./location/within/repository/conformance.yaml [other params for cwl-airflow test]"
    exit 1
fi

echo "Running tests for ${REPO_URL} from file ${SUITE} with CWL-Airflow==${CWL_AIRFLOW_VERSION}"

TEMP="${DIR}/temp"
echo "Cleaning temporary directory ${TEMP}"
rm -rf ${TEMP} && mkdir ${TEMP}

echo "Setting environment variables for docker-compose"
export AIRFLOW_ENV_FILE="${TEMP}/airflow_settings.env"
echo "AIRFLOW__CORE__PARALLELISM=1" >> ${AIRFLOW_ENV_FILE}
echo "AIRFLOW__CORE__DAG_CONCURRENCY=1" >> ${AIRFLOW_ENV_FILE}
echo "AIRFLOW__SCHEDULER__DAG_DIR_LIST_INTERVAL=60" >> ${AIRFLOW_ENV_FILE}
echo "AIRFLOW__CORE__HOSTNAME_CALLABLE=socket.gethostname" >> ${AIRFLOW_ENV_FILE}
echo "AIRFLOW__CORE__DAGBAG_IMPORT_TIMEOUT=120" >> ${AIRFLOW_ENV_FILE}


export UBUNTU_VERSION="${UBUNTU_VERSION}"
export PYTHON_VERSION="${PYTHON_VERSION}"
export CWL_AIRFLOW_VERSION="${CWL_AIRFLOW_VERSION}"
export AIRFLOW_HOME="${TEMP}/airflow"
export CWL_TMP_FOLDER="${TEMP}/airflow/cwl_tmp_folder"
export CWL_INPUTS_FOLDER="${TEMP}/airflow/cwl_inputs_folder"
export CWL_OUTPUTS_FOLDER="${TEMP}/airflow/cwl_outputs_folder"
export CWL_PICKLE_FOLDER="${TEMP}/airflow/cwl_pickle_folder"

export AIRFLOW_WEBSERVER_PORT="8080"
export CWL_AIRFLOW_API_PORT="8081"
export MYSQL_ROOT_PASSWORD="admin"
export MYSQL_DATABASE="airflow"
export MYSQL_USER="airflow"
export MYSQL_PASSWORD="airflow"
export MYSQL_PORT="6603"
export MYSQL_DATA="${TEMP}/airflow/mysql_data"

export PROCESS_REPORT_HOST="tester"
export PROCESS_REPORT_PORT="3069"
export PROCESS_REPORT_URL="http://${PROCESS_REPORT_HOST}:${PROCESS_REPORT_PORT}"

echo "Cleaning old images"  # image names are based on the docker-compose file and should be updated manually if that file was changed
docker rmi --force local_executor_apiserver local_executor_scheduler local_executor_webserver

echo "Building and starting docker-compose as daemon"
DOCKER_COMPOSE_FILE="${DIR}/../../packaging/docker_compose/local_executor/docker-compose.yml"
docker-compose -f ${DOCKER_COMPOSE_FILE} build --no-cache  # need --no-cache as we want to have the latest commit for CWL-Airflow, but its Dockerfile is not changed
docker-compose -f ${DOCKER_COMPOSE_FILE} up -d

echo "Sleeping 60 sec to let all services start"
sleep 60

echo "Cloning repository with tests ${REPO_URL}"
mkdir -p ${AIRFLOW_HOME}
cd ${AIRFLOW_HOME}
git clone ${REPO_URL} --recursive
REPO_FOLDER=`basename ${REPO_URL}`
REPO_FOLDER="${REPO_FOLDER%.*}"      # to exclude possible .git in the url
cd -

echo "Starting docker container to run tests from ${SUITE}"
docker run --rm \
--name "${PROCESS_REPORT_HOST}" \
--hostname "${PROCESS_REPORT_HOST}" \
-v "${AIRFLOW_HOME}:${AIRFLOW_HOME}" \
--network local_executor_default \
local_executor_scheduler \
/bin/bash -c \
"cwl-airflow test --api http://apiserver:${CWL_AIRFLOW_API_PORT} --host 0.0.0.0 --port ${PROCESS_REPORT_PORT} --suite ${AIRFLOW_HOME}/${REPO_FOLDER}/${SUITE} ${PARAMS} > ${AIRFLOW_HOME}/tests.log"

EXIT_CODE=`echo $?`  # to keep exit code while we are stoping docker-compose

echo "Stoping running docker containers"
docker-compose -f ${DOCKER_COMPOSE_FILE} down

exit ${EXIT_CODE}