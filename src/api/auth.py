from functools import wraps

from flask import request

API_KEY_HEADER_KEY = "API-KEY"


class Authorization:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def is_authenticated(self) -> bool:
        header_api_key = request.headers.get(API_KEY_HEADER_KEY)
        query_api_key = request.args.get("apikey")

        if not header_api_key and not query_api_key:
            return False

        if header_api_key == self.api_key or query_api_key == self.api_key:
            return True

        return False

    def should_be_authenticated(self, f):
        @wraps(f)
        def wrap(*args, **kwargs):
            if not self.is_authenticated():
                return "Not Authorized", 401

            return f(*args, **kwargs)

        return wrap
