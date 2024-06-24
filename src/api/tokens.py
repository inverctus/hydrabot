from flask import Blueprint
from flask_pydantic import validate
from pydantic import BaseModel

from api.auth import Authorization
from database.session_factory import SessionFactory
from database.token_store import TokenStore
from settings import SettingsFactory

api_settings = SettingsFactory.get_api_settings()
auth = Authorization(api_settings["api_key"])
session_factory = SessionFactory(api_settings["database_uri"])

tokens_blueprint = Blueprint("tokens", __name__, url_prefix="/tokens")


class TokensQuery(BaseModel):
    skip: int = 0
    limit: int = 100


@tokens_blueprint.route("/", methods=["GET"])
@auth.should_be_authenticated
@validate()
def get_tokens(query: TokensQuery):
    with session_factory.session() as session:
        tokens = TokenStore(session).get_tokens(skip=query.skip, limit=query.limit)

        return {"tokens": [token.asdict() for token in tokens]}, 200


@tokens_blueprint.route("/<token_address>", methods=["GET"])
@auth.should_be_authenticated
@validate()
def get_token(token_address: str):
    with session_factory.session() as session:
        token = TokenStore(session).get_token(token_address)

        if not token:
            return "Not Found", 404

        return token.asdict(), 200
