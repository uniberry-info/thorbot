from royalnet.typing import *
import flask
import flask_sqlalchemy
import authlib.integrations.flask_client
import os
from .database.base import Base


app = flask.Flask(__name__)
app.config.update(**os.environ)

db = flask_sqlalchemy.SQLAlchemy(app=app, metadata=Base.metadata)

oauth = authlib.integrations.flask_client.OAuth(app=app)
oauth.register(
    name="google",
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    api_base_url="https://www.googleapis.com/",
    client_kwargs={
        "scope": "email profile openid",
    },
)


@app.route("/login")
def page_login():
    return oauth.google.authorize_redirect(flask.url_for("page_authorize", _external=True))


@app.route("/authorize")
def page_authorize():
    token = oauth.google.authorize_access_token()
    userinfo = oauth.google.parse_id_token(token=token)
    breakpoint()
    return "OK!"


if __name__ == "__main__":
    app.run(port=30008)
