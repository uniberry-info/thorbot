FROM python:3.8 AS metadata
LABEL maintainer="Stefano Pigozzi <me@steffo.eu>"

FROM metadata AS workdir
WORKDIR /usr/src/thorunimore

FROM workdir AS poetry
RUN pip install "poetry"

FROM poetry AS dependencies
COPY pyproject.toml ./pyproject.toml
COPY poetry.lock ./poetry.lock
RUN poetry install --no-root --no-dev

FROM dependencies AS package
COPY . .
RUN poetry install

FROM package AS environment
ENV PYTHONUNBUFFERED=1

FROM environment AS telegram
ENTRYPOINT ["poetry", "run", "python", "-m", "thorunimore.telegram"]
CMD []

FROM environment AS web
ENTRYPOINT ["poetry", "run", "gunicorn", "-b", "0.0.0.0:80", "thorunimore.web.__main__:reverse_proxy_app"]
CMD []