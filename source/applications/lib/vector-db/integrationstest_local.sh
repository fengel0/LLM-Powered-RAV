#export EMBEDDING_HOST=10.0.0.12:8085
#export RERANKER_HOST="https://vllm.home-vtr4v3n.de"
#export MODEL_RERANKER=BAAI/bge-reranker-base
#export RERANKER_API_KEY="my-dummy-key"

export EMBEDDING_HOST=192.168.83.16:8080
export RERANKER_HOST=http://192.168.83.16:7998
export MODEL_RERANKER=Qwen/Qwen3-Reranker-0.6B
export RERANKER_API_KEY="my-dummy-key"
./integrationstest.sh


