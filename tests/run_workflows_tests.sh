
REPO_URL="https://github.com/datirium/workflows.git"
SUITE="tests/conformance_tests.yaml"
BRANCH=`git rev-parse --abbrev-ref HEAD`

echo "Running tests for ${REPO_URL} from file ${SUITE} with CWL-Airflow==${BRANCH}"
./conformance_tests/test_conformance.sh ${REPO_URL} ${SUITE} ${BRANCH}