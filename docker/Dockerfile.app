FROM --platform=linux/amd64 python:3.11.5-slim AS builder

WORKDIR /project

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV POETRY_VERSION 1.6.1

RUN pip install --upgrade pip
RUN pip install "poetry==$POETRY_VERSION"

COPY ./pyproject.toml ./pyproject.toml
COPY ./poetry.lock ./poetry.lock
COPY ./poetry.toml ./poetry.toml

RUN poetry install --no-root --no-interaction --no-ansi --without dev --compile

COPY ./docker/entrypoint.sh ./entrypoint.sh
COPY ./app/ ./app/

RUN poetry install --sync --no-interaction --no-ansi --without dev --compile

FROM --platform=linux/amd64 python:3.11.5-slim AS executor

WORKDIR /project

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y \
    xvfb \
    chromium \
    chromium-driver

COPY --from=builder /project/.venv /project/.venv
COPY --from=builder /project/entrypoint.sh /project/entrypoint.sh
COPY --from=builder /project/app/ /project/app/

CMD [ "/bin/bash", "/project/entrypoint.sh" ]
