# Logging
export LOG_LEVEL="info"
export LOG_SECRETS=false

export RAG_TYPE="graph"

export POSTGRES_HOST="127.0.0.1"
export POSTGRES_PORT="5432"
export POSTGRES_DATABASE="production-db"
export POSTGRES_USER="root"
export POSTGRES_PASSWORD="password-v2"
export EMBEDDING_SIZE=2560

# S3 Configuration
export S3_HOST="127.0.0.1:9000"
export S3_ACCESS_KEY="root"
export S3_SECRET_KEY="password-v2"
export S3_SESSION_KEY=""
export S3_IS_SECURE=false

export NEO4J_HOST=bolt://127.0.01:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=password-v2

export DEFAULT_CONFIG=e93f83eb-d3ad-4211-ab88-fdf955ed0fa3

# OpenTelemetry Configuration
export OTEL_HOST="127.0.0.1:4317"
export OTEL_ENABLED=true
export OTEL_INSECURE=true

# Qdrant Vector DB Configuration
export QDRANT_HOST="127.0.0.1"
export QDRANT_PORT=6333
export QDRANT_API_KEY=""
export QDRANT_GRPC_PORT=6334
export QDRANT_PREFER_GRPC=true
export VECTOR_COLLECTION="vector_store"
export TOP_N_COUNT_DENSE=10
export TOP_N_COUNT_SPARSE=10
export TOP_N_COUNT_RERANKER=10
export CHUNK_SIZE=512
export CHUNK_OVERLAP=64
export VECTOR_BATCH_SIZE=20

# LLM Configuration
export OPENAI_HOST="http://192.168.83.3:11434/v1"
export DEFAULT_LLM_MODEL="llama3.3:70b"
export RERANK_HOST="http://127.0.0.1:7998"
export RERANK_API_KEY="my-dummy-key"
export IS_EMBEDDING_HOST_SECURE=false
export EMBEDDING_HOST="192.168.83.16:8080"
export IS_RERANK_HOST_SECURE=false

# General Configuration
export PORT=1234
export WORKERS=1
#export RUNNING_HOST="https://we.ai.fh-erfurt.de"
export PATH_PREFIX="/test"

export LLMS_AVAILABALE="llama3.3,deepseek-r1:70b"

# Start application
python src/simple_rag_api/main.py
