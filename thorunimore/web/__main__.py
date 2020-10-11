import os
import re

import authlib.integrations.base_client
import authlib.integrations.flask_client
import flask
import flask_sqlalchemy
import werkzeug.middleware.proxy_fix
from royalnet.typing import *

from ..database import Student
from ..database.base import Base
from ..deeplinking import DeepLinking


app = flask.Flask(__name__)
app.config.update(**os.environ)

reverse_proxy_app = werkzeug.middleware.proxy_fix.ProxyFix(app=app, x_for=1, x_proto=0, x_host=1, x_port=0, x_prefix=0)

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


@app.route("/")
def page_index():
    return flask.render_template("info.html")


@app.route("/login")
def page_login():
    return oauth.google.authorize_redirect(flask.url_for("page_authorize", _external=True))


@app.route("/authorize")
def page_authorize():
    try:
        token = oauth.google.authorize_access_token()
    except werkzeug.exceptions.BadRequestKeyError:
        return flask.render_template(
            "error.html",
            error="Mancano i parametri query necessari per effettuare l'autenticazione OAuth.",
            tip='Torna all\'indice e rifai tutto da capo. Se il problema persiste, contatta '
                '<a href="https://t.me/Steffo">@Steffo</a>!'
        ), 401
    except authlib.integrations.base_client.errors.OAuthError:
        return flask.render_template(
            "error.html",
            error="Qualcosa è andato storto durante l'autenticazione.",
            tip='Torna all\'indice e rifai tutto da capo. Se il problema persiste, contatta '
                '<a href="https://t.me/Steffo">@Steffo</a>!'
        ), 401
    userinfo = oauth.google.parse_id_token(token=token)

    if not userinfo.email_verified:
        return flask.render_template(
            "error.html",
            error="L'email del tuo account Google non è verificata.",
            tip='Probabilmente hai effettuato l\'accesso con l\'email sbagliata. Fai il '
                '<a href="https://accounts.google.com/logout">logout</a> da tutti i tuoi account Google e riprova!'
        ), 403
    email_prefix_match = re.match(r"(.+)@studenti\.unimore\.it", userinfo.email)
    if not email_prefix_match:
        return flask.render_template(
            "error.html",
            error="Questo account Google non appartiene a Studenti Unimore Informatica.",
            tip='Probabilmente hai effettuato l\'accesso con l\'email sbagliata. Fai il '
                '<a href="https://accounts.google.com/logout">logout</a> da tutti i tuoi account Google e riprova!',
        ), 403
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
    if len(state) > 64:
        return flask.render_template("longer.html", state=state), 500

    return flask.redirect(f"https://t.me/{app.config['TELEGRAM_BOT_USERNAME']}?start={state}")


if __name__ == "__main__":
    db.create_all()
    app.run()
