from flask import Flask

from api.events import events_blueprint
from api.pairs import pairs_blueprint
from api.tokens import tokens_blueprint
from settings import SettingsFactory


def create_app() -> Flask:
    app = Flask("hydrabot_api")

    app.register_blueprint(events_blueprint)
    app.register_blueprint(tokens_blueprint)
    app.register_blueprint(pairs_blueprint)

    return app


if __name__ == "__main__":
    api_settings = SettingsFactory.get_api_settings()

    app = create_app()
    app.run(host=api_settings["api_host"])
