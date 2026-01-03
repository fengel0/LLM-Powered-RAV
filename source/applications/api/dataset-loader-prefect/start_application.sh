export LOG_LEVEL=info
export LOG_SECRETS=True

export POSTGRES_HOST="127.0.0.1"
export POSTGRES_PORT="5432"
export POSTGRES_DATABASE="production-db"
export POSTGRES_USER="root"
export POSTGRES_PASSWORD="password-v2"

export OTEL_HOST="127.0.0.1:4317"
export OTEL_ENABLED=true
export OTEL_INSECURE=true

export PREFECT_API_URL=http://0.0.0.0:4200/api
#export PREFECT_API_URL=https://prefrect.home-vtr4v3n.de/api
export OBSERVE_DIR=./test_files


python src/dataset_loader_prefect/main.py
