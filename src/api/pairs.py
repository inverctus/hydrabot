from flask import Blueprint
from flask_pydantic import validate
from pydantic import BaseModel

from api.auth import Authorization
from database.pair_store import PairStore
from database.session_factory import SessionFactory
from settings import SettingsFactory

api_settings = SettingsFactory.get_api_settings()
auth = Authorization(api_settings["api_key"])
session_factory = SessionFactory(api_settings["database_uri"])

pairs_blueprint = Blueprint("pairs", __name__, url_prefix="/pairs")


class PairsQuery(BaseModel):
    chain: str | None = None
    dex: str | None = None
    skip: int = 0
    limit: int = 100


@pairs_blueprint.route("/", methods=["GET"])
@auth.should_be_authenticated
@validate()
def get_pairs(query: PairsQuery):
    with session_factory.session() as session:
        pairs = PairStore(session).get_pairs(
            chain=query.chain, dex=query.dex, skip=query.skip, limit=query.limit
        )

        return {"pairs": [pair.asdict() for pair in pairs]}, 200


@pairs_blueprint.route("/<pair_address>", methods=["GET"])
@auth.should_be_authenticated
@validate()
def get_pair(pair_address: str):
    with session_factory.session() as session:
        pair = PairStore(session).get_pair(pair_address)

        if not pair:
            return "Not Found", 404

        return pair.asdict(), 200
