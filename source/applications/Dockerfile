ARG PYTHON_VERSION=3.12.9

FROM python:${PYTHON_VERSION}-slim-bullseye AS builder
ARG API_FOLDER
ARG ADDITION_PACKES

# Set environment variables
ENV UV_SYSTEM_PYTHON=1 
ENV UV_NO_EDITABLE=1        
ENV UV_COMPILE_BYTECODE=1   
ENV PYTHONDONTWRITEBYTECODE=1 
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV API_FOLDER=${API_FOLDER}


WORKDIR /app


RUN apt-get update && \
  apt-get install -y --no-install-recommends build-essential curl && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.7.15 /uv /uvx /bin/
ENV PATH="/root/.local/bin/:$PATH"

COPY "./api/${API_FOLDER}/requirements.txt" "/app/"
RUN uv pip install --system -r ./requirements.txt

WORKDIR /app
COPY ./lib /app/lib
COPY ./services /app/services
COPY ./api/deployment-base /app/api/deployment-base
COPY ./pyproject.toml /app/

WORKDIR "/app/api/${API_FOLDER}/"
COPY "./api/${API_FOLDER}/*" ./
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
COPY "./api/${API_FOLDER}/dependencies.sh" ./
RUN chmod +x ./dependencies.sh
RUN ./dependencies.sh

WORKDIR "/app/api/${API_FOLDER}/src"
COPY ./lib /app/lib
COPY ./services /app/services
COPY ./api/deployment-base /app/api/deployment-base
COPY "./api/${API_FOLDER}/src" ./
RUN chmod +x ./start.sh

EXPOSE 8000

CMD ["sh", "./start.sh"]
