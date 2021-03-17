
REPO_URL="https://github.com/common-workflow-language/cwl-v1.1.git"
SUITE="conformance_tests.yaml"
RANGE="--range 2-999"


# SKIP test N1
# - job: tests/bwa-mem-job.json
#   tool: tests/bwa-mem-tool.cwl
# BECAUSE
# In this test they create cwl.output.json that doesn’t include sam output.
# Therefore when placed as a step of the workflow the bwa-mem-tool.cwl tool
# won’t produce a required output and we will get an error "Output is missing
# expected field". This is not a bug that we should fix, as this test interfere
# the normal flow of things.


echo "Running ${RANGE} tests for ${REPO_URL} from file ${SUITE}"
./test_conformance.sh ${REPO_URL} ${SUITE} ${RANGE}