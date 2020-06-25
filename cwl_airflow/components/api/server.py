#!/usr/bin/env python
import connexion
from connexion.resolver import Resolver

from cwl_airflow.components.api.backend import CWLApiBackend


def run_api_server(args):
    app = connexion.FlaskApp(
        __name__,
        host=args.host,
        port=args.port,
        specification_dir="openapi",
        server="tornado"
    )
    backend = CWLApiBackend()
    app.add_api(
        specification="swagger_configuration.yaml",
        resolver=Resolver(lambda x: getattr(backend, x))
    )
    app.run()