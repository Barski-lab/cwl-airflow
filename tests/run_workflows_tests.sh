
REPO_URL="https://github.com/datirium/workflows.git"
SUITE="tests/conformance_tests.yaml"

echo "Running tests for ${REPO_URL} from file ${SUITE}"
./test_conformance.sh ${REPO_URL} ${SUITE}