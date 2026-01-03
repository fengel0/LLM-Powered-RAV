export EMBEDDING_HOST=10.0.0.12:8085
export EMBEDDING_SIZE=768

export OPENAI_HOST=https://ollama.home-vtr4v3n.de/v1
export OPENAI_MODEL=llama3.2
export OPENAI_HOST_KEY=dummy

export RERANKER_HOST="https://vllm.home-vtr4v3n.de"
export MODEL_RERANKER=BAAI/bge-reranker-base
export RERANKER_API_KEY="my-dummy-key"

./end_to_end_test.sh
