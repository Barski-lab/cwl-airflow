#!/usr/bin/env python
import connexion
from connexion.resolver import Resolver

from cwl_airflow.components.api.backend import CWLAirflowBackend


def run_api_server(args):
    app = connexion.App(__name__)
    backend = CWLAirflowBackend()
    def rs(x):
        return getattr(backend, x.split('.')[-1])
    app.add_api('openapi/swagger_configuration.yaml', resolver=Resolver(rs))
    app.run(port=args.port, host=args.host)