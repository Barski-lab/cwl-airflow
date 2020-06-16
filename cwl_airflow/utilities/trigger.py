#! /usr/bin/env python3
import sys
import argparse
import requests
import jwt
from future.moves.urllib.parse import urljoin


public_key = b"""-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDdlatRjRjogo3WojgGHFHYLugd
UWAY9iR3fy4arWNA1KoS8kVw33cJibXr8bvwUAUparCwlvdbH6dvEOfou0/gCFQs
HUfQrSDv+MuSUMAe8jzKE4qW+jK+xQU9a03GUnKHkkle+Q0pX/g6jXZ7r1/xAK5D
o2kQ+X5xK9cipRgEKwIDAQAB
-----END PUBLIC KEY-----
"""


private_key = b"""-----BEGIN RSA PRIVATE KEY-----
MIICWwIBAAKBgQDdlatRjRjogo3WojgGHFHYLugdUWAY9iR3fy4arWNA1KoS8kVw
33cJibXr8bvwUAUparCwlvdbH6dvEOfou0/gCFQsHUfQrSDv+MuSUMAe8jzKE4qW
+jK+xQU9a03GUnKHkkle+Q0pX/g6jXZ7r1/xAK5Do2kQ+X5xK9cipRgEKwIDAQAB
AoGAD+onAtVye4ic7VR7V50DF9bOnwRwNXrARcDhq9LWNRrRGElESYYTQ6EbatXS
3MCyjjX2eMhu/aF5YhXBwkppwxg+EOmXeh+MzL7Zh284OuPbkglAaGhV9bb6/5Cp
uGb1esyPbYW+Ty2PC0GSZfIXkXs76jXAu9TOBvD0ybc2YlkCQQDywg2R/7t3Q2OE
2+yo382CLJdrlSLVROWKwb4tb2PjhY4XAwV8d1vy0RenxTB+K5Mu57uVSTHtrMK0
GAtFr833AkEA6avx20OHo61Yela/4k5kQDtjEf1N0LfI+BcWZtxsS3jDM3i1Hp0K
Su5rsCPb8acJo5RO26gGVrfAsDcIXKC+bQJAZZ2XIpsitLyPpuiMOvBbzPavd4gY
6Z8KWrfYzJoI/Q9FuBo6rKwl4BFoToD7WIUS+hpkagwWiz+6zLoX1dbOZwJACmH5
fSSjAkLRi54PKJ8TFUeOP15h9sQzydI8zJU+upvDEKZsZc/UhT/SySDOxQ4G/523
Y0sz/OZtSWcol/UMgQJALesy++GdvoIDLfJX5GBQpuFgFenRiRDabxrE9MNUZ2aP
FaFp+DyAe+b4nDwuJaW2LURbr8AEZga7oQj0uYxcYw==
-----END RSA PRIVATE KEY-----
"""


def get_parser():
    parser = argparse.ArgumentParser(description='DAG trigger', add_help=True)
    parser.add_argument("-d", "--dag",  help="Dag id",                          required=True)
    parser.add_argument("-r", "--run",  help="Run id",                          required=True)
    parser.add_argument("-c", "--conf", help="Configuration, json-like string", required=True)
    parser.add_argument("-a", "--alg",  help="JWT algorithm",                   default="RS256")
    parser.add_argument("-u", "--url",  help="API url, with port number",       default="http://localhost:8080")
    return parser


def trigger_dag(dag_id, run_id, api_url, conf, alg):
    json_data = {
        "run_id": run_id,
        "conf": conf
    }
    json_data["token"] = jwt.encode(json_data, private_key, algorithm=alg).decode("utf-8")
    return requests.post(url=urljoin(api_url, f"""/api/experimental/dags/{dag_id}/dag_runs"""),
                         json=json_data)


def main(argsl=None):
    if argsl is None:
        argsl = sys.argv[1:]
    args,_ = get_parser().parse_known_args(argsl)
    res = trigger_dag(args.dag, args.run, args.url, args.conf, args.alg)
    print(res.text)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))