
REPO_URL="https://github.com/common-workflow-language/cwl-v1.2.git"
SUITE="conformance_tests.yaml"

echo "Running tests for ${REPO_URL} from file ${SUITE}"
./conformance_tests/test_conformance.sh ${REPO_URL} ${SUITE}