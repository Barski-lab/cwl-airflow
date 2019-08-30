#!/usr/bin/env python
import sys
import argparse
from cwl_airflow.wes.server import run_wes_server


def arg_parser():
    parent_parser = argparse.ArgumentParser(add_help=False)
    general_parser = argparse.ArgumentParser(description='cwl-airflow')
    subparsers = general_parser.add_subparsers()
    subparsers.required = True

    wes_parser = subparsers.add_parser('apiserver', help="Running CWL-Airflow API server", parents=[parent_parser])
    wes_parser.set_defaults(func=run_wes_server)
    wes_parser.add_argument("--port",  dest="port",  type=int,            help="Port to run API server (default: 8081)",      default=8081)
    wes_parser.add_argument("--host",  dest="host",                       help="Host to run API server (default: 127.0.0.1)", default="127.0.0.1")

    return general_parser


def main(argsl=None):
    if argsl is None:
        argsl = sys.argv[1:]
    argsl.append("")  # To avoid raising error when argsl is empty
    args, _ = arg_parser().parse_known_args(argsl)
    args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))