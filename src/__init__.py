from flask import Flask
import os


def create_app(config=None):

    app = Flask(__name__)
    if config is None:
        config = os.environ.get("config", "src.config.DevelopmentConfig")

    app.config.from_object(config)
    from .views import slackapp

    app.register_blueprint(slackapp)

    return app


app = create_app()
