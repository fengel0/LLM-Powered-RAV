export LOG_LEVEL=debug
export WOKERS=1
export PORT=1234
export LOG_SECRETS=True

export S3_HOST=127.0.0.1:9000
export S3_ACCESS_KEY=root
export S3_SECRET_KEY=password
export S3_SESSION_KEY=
export S3_IS_SECURE=false

export S3_IS_SECURE=false
export DEVICE=cuda #cuda, mps, cpu

export OTEL_HOST="127.0.0.1:4317"
export OTEL_ENABLED=false
export OTEL_INSECURE=true

python src/file_converter_api/main.py
