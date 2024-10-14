FROM python:3.10-slim

WORKDIR /app

# Install poetry
RUN pip install poetry==1.6.1

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Copy pyproject.toml and poetry.lock
COPY pyproject.toml ./
COPY poetry.lock ./
COPY README.md ./

RUN mkdir -p worker
RUN touch worker/__init__.py

# Install dependencies using poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

COPY . .
RUN poetry install --no-interaction --no-ansi

CMD ["poetry", "run", "celery", "--app=worker.app", "worker", "--loglevel=info"]
