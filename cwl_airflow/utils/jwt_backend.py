import jwt
from functools import wraps
from flask import request, Response
from airflow.models import Variable


client_auth = None


def init_app(app):
    pass


def requires_authentication(function):
    @wraps(function)
    def decorated(*args, **kwargs):
        PUBLIC_KEY = "jwt_backend_public_key"
        ALGORITHM = "jwt_backend_algorithm"
        try:
            json_data = {k: v for k, v in request.get_json(force=True).copy().items() if k != "token"}
            decoded_token = jwt.decode(request.get_json(force=True)["token"], Variable.get(PUBLIC_KEY), algorithms=Variable.get(ALGORITHM))
            assert (json_data == decoded_token)
        except Exception:
            return Response("Failed to verify data", 403)
        return function(*args, **kwargs)
    return decorated
