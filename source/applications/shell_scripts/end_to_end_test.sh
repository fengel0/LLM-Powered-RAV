
#!/usr/bin/env bash
# Führt Integrationstests für ausgewählte Python-Libraries aus
# -----------------------------------------------------------
set -euo pipefail

START_DIR="$(pwd)"

#export OLLAMA_HOST=http://192.168.83.3:11434
export OLLAMA_HOST=https://ollama.home-vtr4v3n.de
export OLLAMA_MODEL=llama3.2


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


# ---------- Libraries, die getestet werden ----------
libraries=(
  dataset-file-loader-prefect
  dataset-loader-prefect
  file-uploader-prefect
  file-converter-prefect
  file-embedding-prefect
  grading-prefect
  rag-prefect
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
    cd "${START_DIR}/api/${name}"
    ./end_to_end_test.sh
    ((idx++))
  done
}

# ---------- Ausführung ----------
print_header "Integrationstests für Python-Libraries"
run_integrations

echo -e "\n${bold}${magenta}Alle End-To-End-Tests abgeschlossen.${reset}"

