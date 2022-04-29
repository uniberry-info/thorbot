import os
import re

import authlib.integrations.base_client
import authlib.integrations.flask_client
import flask
import flask_sqlalchemy
import werkzeug.middleware.proxy_fix
from royalnet.typing import *

from ..database import Student, Token, Telegram
from ..database.base import Base
from ..deeplinking import DeepLinking


app = flask.Flask(__name__)
app.config.update(**os.environ)

# noinspection PyArgumentEqualDefault
reverse_proxy_app = werkzeug.middleware.proxy_fix.ProxyFix(app=app, x_for=1, x_proto=1, x_host=1, x_port=0, x_prefix=0)

db = flask_sqlalchemy.SQLAlchemy(app=app, metadata=Base.metadata)
db.create_all()

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


@app.route("/privacy")
def page_privacy():
    return flask.render_template("privacy.html")


@app.route("/api/<token>/whois/<int:tg_id>")
def api_whois(token: str, tg_id: int):
    token = db.session.query(Token).filter_by(token=token).one_or_none()
    if token is None:
        return flask.jsonify({
            "description": "Invalid token",
        }), 403

    tg = db.session.query(Telegram).filter_by(id=tg_id).one_or_none()
    if tg is None:
        return flask.jsonify({
            "description": "User was not found in Thor's database",
            "found": False,
        }), 404

    if tg.st.privacy:
        return flask.jsonify({
            "description": "User has a private profile in Thor's database",
            "found": True,
        }), 200

    return flask.jsonify({
        "description": "User has a public profile in Thor's database",
        "found": True,
        "tg": {
            "first_name": tg.first_name,
            "last_name": tg.last_name,
            "username": tg.username,
        },
        "st": {
            "email": f"{tg.st.email_prefix}@studenti.unimore.it",
            "first_name": tg.st.first_name,
            "last_name": tg.st.last_name,
        }
    }), 200


def main():
    app.run()


if __name__ == "__main__":
    main()
