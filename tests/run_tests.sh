#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

pytest -v --forked $DIR/test_helpers.py && \
pytest -v --forked $DIR/test_parser.py && \
pytest -v --forked $DIR/test_init_config.py && \
pytest -v --forked $DIR/test_cwl.py