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

# General Configuration
export PORT=1234
export GRADIO_SERVER_NAME=0.0.0.0

# Start application
python src/graph_view/main.py
