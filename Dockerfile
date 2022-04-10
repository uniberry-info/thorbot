FROM python:3.8 AS metadata
LABEL maintainer="Stefano Pigozzi <me@steffo.eu>"
WORKDIR /usr/src/thorunimore

FROM metadata AS poetry
RUN pip install "poetry==1.1.12"

FROM poetry AS dependencies
COPY pyproject.toml ./pyproject.toml
COPY poetry.lock ./poetry.lock
RUN poetry install --no-root --no-dev
RUN pip install gunicorn

FROM dependencies AS package
COPY . .
RUN poetry install

FROM package AS environment
ENV PYTHONUNBUFFERED=1

FROM environment AS telegram
ENTRYPOINT ["poetry", "run", "python", "-m", "impressive_strawberry.telegram"]

FROM environment AS web
ENTRYPOINT ["gunicorn", "-b", "0.0.0.0:80", "impressive_strawberry.web.__main__:reverse_proxy_app"]
