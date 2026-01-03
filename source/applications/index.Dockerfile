ARG PYTHON_VERSION=3.12.9

FROM python:${PYTHON_VERSION}-slim-bullseye AS builder
ARG API_FOLDER

# Set environment variables
ENV UV_SYSTEM_PYTHON=1 
ENV UV_NO_EDITABLE=1        
ENV UV_COMPILE_BYTECODE=1   
ENV PYTHONDONTWRITEBYTECODE=1 
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1


WORKDIR /app


RUN apt-get update && \
  apt-get install -y --no-install-recommends build-essential curl && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.7.15 /uv /uvx /bin/
ENV PATH="/root/.local/bin/:$PATH"

COPY "./api/file-index-prefect/requirements.txt" "/app/"
RUN uv pip install --system -r ./requirements.txt

WORKDIR /app
COPY ./lib /app/lib
COPY ./services /app/services
COPY ./api/ /app/api
COPY ./pyproject.toml /app/

WORKDIR "/app/api/file-index-prefect/"
COPY "./api/file-index-prefect/*" ./
RUN uv pip compile pyproject.toml --output-file requirements.txt
RUN uv pip install --system -r ./requirements.txt


# Command to run the application
FROM python:${PYTHON_VERSION}-slim-bullseye 
ARG API_FOLDER
ARG UID=10001

RUN adduser --disabled-password --gecos "" --home "/nonexistent" \
  --shell "/sbin/nologin" --no-create-home --uid "${UID}" appuser

RUN apt-get update && \
  apt-get install -y --no-install-recommends curl && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY "./api/file-index-prefect/dependencies.sh" ./
RUN chmod +x ./dependencies.sh
RUN ./dependencies.sh

WORKDIR "/app/api/file-index-prefect/src"
COPY ./lib /app/lib
COPY ./services /app/services
COPY ./api/ /app/api
COPY "./api/file-index-prefect/src" ./
RUN chmod +x ./start.sh

EXPOSE 8000

CMD ["sh", "./start.sh"]
