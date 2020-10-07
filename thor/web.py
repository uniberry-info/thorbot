from royalnet.typing import *
import flask
import flask_sqlalchemy
import authlib.integrations.flask_client
import os
import itsdangerous.url_safe
from .database.base import Base
from .database import Student


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

serializer = itsdangerous.url_safe.URLSafeSerializer(app.secret_key)


@app.route("/login")
def page_login():
    return oauth.google.authorize_redirect(flask.url_for("page_authorize", _external=True))


@app.route("/authorize")
def page_authorize():
    token = oauth.google.authorize_access_token()
    userinfo = oauth.google.parse_id_token(token=token)
    if not (userinfo.email_verified and userinfo.email.endswith("@studenti.unimore.it")):
        return flask.abort(403)

    new_student = Student(
        email=userinfo.email,
        first_name=userinfo.given_name,
        last_name=userinfo.family_name
    )
    db.session.add(new_student)
    db.session.commit()

    state = serializer.dumps(new_student.email)
    return flask.redirect(f"https://t.me/{app.config['TELEGRAM_BOT_USERNAME']}?start=register:{state}")


if __name__ == "__main__":
    db.create_all()
    app.run()
