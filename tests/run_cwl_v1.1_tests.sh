
REPO_URL="https://github.com/common-workflow-language/cwl-v1.1.git"
SUITE="conformance_tests.yaml"

echo "Running tests for ${REPO_URL} from file ${SUITE}"
./test_conformance.sh ${REPO_URL} ${SUITE}