# Logging
export LOG_LEVEL="info"
export LOG_SECRETS=true

# OpenTelemetry Configuration
export OTEL_HOST="127.0.0.1:4317"
export OTEL_ENABLED=false
export OTEL_INSECURE=true

export POSTGRES_HOST="127.0.0.1"
export POSTGRES_PORT="5432"
export POSTGRES_DATABASE="production-db"
export POSTGRES_USER="root"
export POSTGRES_PASSWORD="password-v2"


# Start application
#python -m unittest tests/store_question.py
python -m unittest tests/llm_eval.py

