#! /usr/bin/env python3

import cwltool.load_tool as load
from cwltool.context import LoadingContext
from airflow.configuration import conf
from airflow.exceptions import AirflowConfigException
from cwltool.load_tool import (FetcherConstructorType, resolve_tool_uri,
                               fetch_document, make_tool, validate_document)
from cwltool.resolver import tool_resolver
from cwltool.workflow import default_make_tool


def flatten(input_list):
    result = []
    for i in input_list:
        if isinstance(i, list):
            result.extend(flatten(i))
        else:
            result.append(i)
    return result


def conf_get_default(section, key, default):
    try:
        return conf.get(section, key)
    except AirflowConfigException:
        return default


def shortname(n):
    return n.split("#")[-1]


def load_tool(argsworkflow,              # type: Union[Text, Dict[Text, Any]]
              loadingContext             # type: LoadingContext
             ):  # type: (...) -> Process

    document_loader, workflowobj, uri = fetch_document(
        argsworkflow,
        resolver=loadingContext.resolver,
        fetcher_constructor=loadingContext.fetcher_constructor)

    document_loader, avsc_names, _, metadata, uri = validate_document(
        document_loader, workflowobj, uri,
        enable_dev=loadingContext.enable_dev,
        strict=loadingContext.strict,
        fetcher_constructor=loadingContext.fetcher_constructor,
        overrides=loadingContext.overrides_list,
        skip_schemas = True,
        metadata=loadingContext.metadata)

    return make_tool(document_loader,
                     avsc_names,
                     metadata,
                     uri,
                     loadingContext)


def load_cwl(cwl_file, default_args):
    load.loaders = {}
    loading_context = LoadingContext(default_args)
    loading_context.construct_tool_object = default_make_tool
    loading_context.resolver = tool_resolver
    tool = load_tool(cwl_file, loading_context)
    it_is_workflow = tool.tool["class"] == "Workflow"
    return tool, it_is_workflow
