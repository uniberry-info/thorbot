from royalnet.typing import *
import flask
import flask_sqlalchemy
import authlib.integrations.flask_client
import os
import re
from .database.base import Base
from .database import Student
from .deeplinking import DeepLinking


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

dl = DeepLinking(app.secret_key)


@app.route("/login")
def page_login():
    return oauth.google.authorize_redirect(flask.url_for("page_authorize", _external=True))


@app.route("/authorize")
def page_authorize():
    token = oauth.google.authorize_access_token()
    userinfo = oauth.google.parse_id_token(token=token)

    if not userinfo.email_verified:
        return flask.abort(403)
    email_prefix_match = re.match(r"(.+)@studenti\.unimore\.it", userinfo.email)
    if not email_prefix_match:
        return flask.abort(403)
    email_prefix = email_prefix_match.group(1)

    student: Optional[Student] = db.session.query(Student).filter_by(email_prefix=email_prefix).one_or_none()
    if student is None:
        student = Student(
            email_prefix=email_prefix,
            first_name=userinfo.given_name,
            last_name=userinfo.family_name
        )
        db.session.add(student)
    else:
        student.first_name = userinfo.given_name
        student.last_name = userinfo.family_name
    db.session.commit()

    state = dl.encode(("R", student.email_prefix))
    return flask.redirect(f"https://t.me/{app.config['TELEGRAM_BOT_USERNAME']}?start={state}")


if __name__ == "__main__":
    db.create_all()
    app.run()
