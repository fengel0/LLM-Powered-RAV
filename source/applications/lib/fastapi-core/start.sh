export OTEL_LOGS_EXPORTER="otlp"
export OTEL_EXPORTER_OTLP_LOGS_ENDPOINT="http://127.0.0.1:4317"
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf

python src/main.py

