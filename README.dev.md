## **Notes for developers**

When running on MacOS, you might need to set up the following env variable before starting `airflow scheduler/webserver`

```
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
```

**Conformance and unit tests were run for**
- macOS 11.4
  - Python 3.8.6
- Ubuntu 18.04
  - Python 3.6.8
  - Python 3.7.9
  - Python 3.8.10
- Ubuntu 20.04
  - Python 3.6.8
  - Python 3.7.9
  - Python 3.8.10

*For Ubuntu the Python versions were selected based on latest available binary release at the time of testing.

**To run conformance tests in Docker container**
```
cd tests
./run_conformance_tests_docker.sh $UBUNTU_VERSION $PYTHON_VERSION $CWL_AIRFLOW_VERSION $REPO_URL $SUITE
```
**To run unit tests in Docker container**
```
cd tests
./run_unit_tests_docker.sh $UBUNTU_VERSION $PYTHON_VERSION $CWL_AIRFLOW_VERSION
```

**To build rellocatable version in Docker container**
```
cd ./packaging/portable/linux
./pack_linux_docker.sh
```