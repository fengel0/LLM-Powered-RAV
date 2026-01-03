export LOG_LEVEL=info
export LOG_SECRETS=True

# S3 Configuration
export S3_HOST="127.0.0.1:9000"
export S3_ACCESS_KEY="root"
export S3_SECRET_KEY="password"
export S3_SESSION_KEY=""
export S3_IS_SECURE=false

# MongoDB
export POSTGRES_HOST="127.0.0.1"
export POSTGRES_PORT="5432"
export POSTGRES_DATABASE="production-db"
export POSTGRES_USER="root"
export POSTGRES_PASSWORD="password"

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
export RERANK_HOST="127.0.0.1:8084"
export IS_EMBEDDING_HOST_SECURE=false
export EMBEDDING_HOST="127.0.0.1:8080"
export IS_RERANK_HOST_SECURE=false

#export PREFECT_API_URL=https://prefrect.home-vtr4v3n.de/api
export PREFECT_API_URL=http://0.0.0.0:4200/api

python src/file_index_prefect/main.py

