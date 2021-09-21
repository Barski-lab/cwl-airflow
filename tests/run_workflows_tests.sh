UBUNTU_VERSION=$1
PYTHON_VERSION=$2
CWL_AIRFLOW_VERSION=`git rev-parse --abbrev-ref HEAD`
REPO_URL="https://github.com/datirium/workflows.git"
SUITE="tests/conformance_tests.yaml"

echo "Running tests for ${REPO_URL} from the file ${SUITE} with CWL-Airflow ${CWL_AIRFLOW_VERSION}"
echo "using Ubuntu ${UBUNTU_VERSION} and Python ${PYTHON_VERSION}"
./conformance_tests/test_conformance.sh ${UBUNTU_VERSION} ${PYTHON_VERSION} ${CWL_AIRFLOW_VERSION} ${REPO_URL} ${SUITE} 