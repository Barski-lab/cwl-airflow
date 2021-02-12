#!/usr/bin/env python
import logging
import connexion
import threading

from time import sleep
from connexion.resolver import Resolver

from cwl_airflow.utilities.report import resend_reports
from cwl_airflow.components.api.backend import CWLApiBackend


def get_replay_thread(
    replay_interval
):
    """
    Starts thread that will attempt to resend not delivered
    reports every replay_interval seconds. Thread will be
    killed when the main program exits.
    """

    def _resend_loop(replay_interval):
        while True:
            resend_reports()
            sleep(replay_interval)
    return threading.Thread(
        target=_resend_loop,
        daemon=True,
        kwargs={"replay_interval": replay_interval}
    )


def run_api_server(args):
    if args.replay is not None:
        logging.info(f"Will attempt to resend all not delivered reports every {args.replay} seconds")
        replay_thread = get_replay_thread(args.replay)
        replay_thread.start()
    app = connexion.FlaskApp(
        __name__,
        host=args.host,
        port=args.port,
        specification_dir="openapi",
        server="tornado"
    )
    backend = CWLApiBackend(simulated_reports_location=args.simulation)  # when simulated_reports_location points to the valid file the simulation mode will be enabled
    app.add_api(
        specification="swagger_configuration.yaml",
        resolver=Resolver(lambda x: getattr(backend, x))
    )
    app.run()