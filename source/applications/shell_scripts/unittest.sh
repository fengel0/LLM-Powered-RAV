#!/usr/bin/env bash
# Run unit tests for all local Python libs & services
# --------------------------------------------------
set -euo pipefail

START_DIR="$(pwd)"

# --------- Konfiguration ---------
libraries=(
  core
  #database
  #domain
  #fastapi-core
  #file-converter-client
  #file-database
  #llama-index-extension
  text-splitter
  #ollama-client
  #hippo-rag
  #hippo-rag-database
  #hippo-rag-graph
  #hippo-rag-vector-store
  #pdf-converter
  #prefect-core
  #project-database
  #rest-client
  #s3
  #simple-rag
  #text-analysis
  #text-embedding
  #validation-database
  #vector-db
  #word-converter
)

services=(
  #config-service
  #evaluation-service
  file-converter-pipline-service
  file-converter-service
  file-embedding-pipline-service
  file-uploader-service
  grading-service
  image-description-service
  rag-pipline-service
  simple-rag-service
)

# --------- Helper für hübsche Ausgabe ---------
bold=$(tput bold 2>/dev/null || true)
green=$(tput setaf 2 2>/dev/null || true)
cyan=$(tput setaf 6 2>/dev/null || true)
reset=$(tput sgr0 2>/dev/null || true)

print_header() {
  local title="$1"
  echo -e "\n${bold}${cyan}=== ${title} ===${reset}"
}

run_tests() {
  local category="$1"        # "lib" oder "services"
  local base_path="$2"       # Pfad relativ zu START_DIR
  shift 2
  local arr=("$@")

  local total=${#arr[@]}
  local idx=1
  source .venv/bin/activate
  for name in "${arr[@]}"; do
    echo -e "${bold}${green}[${idx}/${total}]${reset} ${name}"
    uv sync --all-extras --package $name
    cd "${START_DIR}/${base_path}/${name}"
    ./unittest.sh
    ((idx++))
  done
  deactivate
  cd $START_DIR
}

# --------- Ausführung ---------
print_header "Unittests für Python-Libraries"
run_tests "lib" "lib" "${libraries[@]}"

print_header "Unittests für Python-Services"
run_tests "service" "services" "${services[@]}"

echo -e "\n${bold}${cyan}Alle Tests abgeschlossen.${reset}"

