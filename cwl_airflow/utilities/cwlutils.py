#! /usr/bin/env python3
import cwltool.load_tool as load

from cwltool.context import LoadingContext
from cwltool.load_tool import (fetch_document, make_tool, resolve_and_validate_document)
from cwltool.resolver import tool_resolver
from cwltool.workflow import default_make_tool


from airflow.configuration import conf
from airflow.exceptions import AirflowConfigException


def flatten(input_list):
    result = []
    for i in input_list:
        if isinstance(i, list):
            result.extend(flatten(i))
        else:
            result.append(i)
    return result


def shortname(n):
    return n.split("#")[-1]



