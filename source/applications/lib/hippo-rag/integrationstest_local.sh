set -e 
#export OPENAI_HOST=https://mokitul.ai.fh-erfurt.de
export OPENAI_HOST=https://ollama.home-vtr4v3n.de/v1
export OPENAI_MODEL=llama3.2
export OPENAI_HOST_KEY=dummy
export EMBEDDING_HOST=10.0.0.12:8085
export EMBEDDING_SIZE=768
./integrationstest.sh


