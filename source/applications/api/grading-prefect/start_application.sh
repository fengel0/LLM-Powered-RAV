export LOG_LEVEL=info
export LOG_SECRETS=True

export POSTGRES_HOST="127.0.0.1"
export POSTGRES_PORT="5432"
export POSTGRES_DATABASE="production-db"
export POSTGRES_USER="root"
export POSTGRES_PASSWORD="password"

export OLLAMA_TIMEOUT=6000
export OLLAMA_HOST="http://we.ai.fh-erfurt.de:20000"
#export OLLAMA_MODEL="gemma3:27b"
#export SYSTEM_NAME="gemma3:27b"
#export CONTEXT_SIZE=8192

export OTEL_HOST="127.0.0.1:4317"
export OTEL_ENABLED=true
export OTEL_INSECURE=true

export PREFECT_API_URL=https://prefrect.home-vtr4v3n.de/api

python src/grading_prefect/main.py
