# Logging
export LOG_LEVEL="info"
export LOG_SECRETS="true"

# MongoDB
export POSTGRES_HOST="127.0.0.1"
export POSTGRES_PORT="5432"
export POSTGRES_DATABASE="production-db"
export POSTGRES_USER="root"
export POSTGRES_PASSWORD="password"

# Ollama / LLM
export OLLAMA_HOST="http://we.ai.fh-erfurt.de:20000"
export OLLAMA_TIMEOUT="6000"
export RAG_TYPE=sub

# Vector DB (Qdrant)
export QDRANT_HOST="127.0.0.1"
export QDRANT_PORT="6333"
export QDRANT_GRPC_PORT="6334"
export QDRANT_API_KEY=""
export QDRANT_PREFER_GRPC="true"
export VECTOR_COLLECTION="123"

# OTEL
export OTEL_ENABLED="true"
export OTEL_HOST="127.0.0.1:4317"
export OTEL_INSECURE="true"

# Embedding + Rerankers
export EMBEDDING_HOST=192.168.83.16:8080
export RERANK_HOST=192.168.83.16:8084
export IS_EMBEDDING_HOST_SECURE="false"
export IS_RERANK_HOST_SECURE="false"

export DEFAULT_LLM_MODEL="gemma3:27b"

# Others
export REQUEST_TIME_OUT="6000"
#export PREFECT_API_URL=https://prefrect.home-vtr4v3n.de/api
export PREFECT_API_URL=http://127.0.0.1:4200/api



# Start the app
python src/rag_prefect/main.py
