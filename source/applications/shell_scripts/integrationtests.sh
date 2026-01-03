#!/usr/bin/env bash
# Führt Integrationstests für ausgewählte Python-Libraries aus
# -----------------------------------------------------------
set -euo pipefail

#export EMBEDDING_HOST=192.168.83.16:8080
export EMBEDDING_HOST=10.0.0.12:8085
#export EMBEDDING_SIZE=2560
export EMBEDDING_SIZE=768


#export OPENAI_HOST=http://192.168.83.3:11434/v1
export OPENAI_HOST=https://ollama.home-vtr4v3n.de/v1
export OPENAI_MODEL=llama3.2
export OPENAI_HOST_KEY=dummy

#export RERANKER_HOST=http://192.168.83.16:7998
export RERANKER_HOST="https://vllm.home-vtr4v3n.de"
export MODEL_RERANKER=BAAI/bge-reranker-base
#export MODEL_RERANKER=Qwen/Qwen3-Reranker-0.6B

export RERANKER_API_KEY="my-dummy-key"


START_DIR="$(pwd)"

# ---------- Libraries, die getestet werden ----------
libraries=(
  database
  file-database
  #ollama-client
  openai-client
  project-database
  hippo-rag-database
  hippo-rag-graph
  hippo-rag
  hippo-rag-vectore-store
  config-database
  fact-store-database
  s3
  text-embedding
  validation-database
  vector-db
)

# ---------- Farben & Helfer ----------
bold=$(tput bold 2>/dev/null || true)
magenta=$(tput setaf 5 2>/dev/null || true)
green=$(tput setaf 2 2>/dev/null || true)
reset=$(tput sgr0 2>/dev/null || true)

print_header() {
  echo -e "\n${bold}${magenta}=== $1 ===${reset}"
}

run_integrations() {
  local total=${#libraries[@]}
  local idx=1
  source .venv/bin/activate
  for name in "${libraries[@]}"; do
    echo -e "${bold}${green}[${idx}/${total}]${reset} Integrationstests für ${name}"
    uv sync --all-extras --package $name
    cd "${START_DIR}/lib/${name}"
    chmod +x ./integrationstest.sh
     ./integrationstest.sh
    ((idx++))
  done
  deactivate
}

# ---------- Ausführung ----------
print_header "Integrationstests für Python-Libraries"
run_integrations

echo -e "\n${bold}${magenta}Alle Integrationstests abgeschlossen.${reset}"

