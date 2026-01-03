#!/usr/bin/env bash
# Führt Integrationstests für Libraries, Services und APIs / Prefect-Flows aus
# ---------------------------------------------------------------------------
set -euo pipefail

START_DIR="$(pwd)"
PROJECT_ROOT="${START_DIR}"

# ------------- Was getestet wird -------------
libraries=(
  config-database
  core
  database
  domain
  domain-test
  fact-store-database
  fastapi-core
  file-converter-client
  file-database
  hippo-rag
  hippo-rag-database
  hippo-rag-graph
  hippo-rag-vectore-store
  llama-index-extension
  openai-client
  pdf-converter
  prefect-core
  project-database
  rest-client
  s3
  simple-rag
  text-embedding
  text-splitter
  validation-database
  vector-db
  word-converter
)

services=(
  config-service
  evaluation-service
  file-converter-pipline-service
  file-converter-service
  file-embedding-pipline-service
  file-uploader-service
  grading-service
  image-description-service
  rag-pipline-service
  simple-rag-service
)

apis=(
  database-migration
  dataset-file-loader-prefect
  dataset-loader-prefect
  deployment-base
  file-converter-api
  file-converter-prefect
  file-embedding-prefect
  file-uploader-prefect
  file-index-prefect
  grading-prefect
  graph-view
  rag-prefect
  simple-rag-api
  trigger-evaluation-prefect
)

# ------------- Farben & Helfer -------------
bold=$(tput bold 2>/dev/null || true)
magenta=$(tput setaf 5 2>/dev/null || true)
green=$(tput setaf 2 2>/dev/null || true)
reset=$(tput sgr0 2>/dev/null || true)

print_section() {             # $1 = Überschrift
  echo -e "\n${bold}${magenta}=== $1 ===${reset}"
}

run_integrations() {          # $1 = Basis-Pfad, $2… = Einträge
  local base_path="$1"; shift
  local elements=("$@")
  local total=${#elements[@]}
  local idx=1
  source .venv/bin/activate
  for name in "${elements[@]}"; do
    echo -e "${bold}${green}[${idx}/${total}]${reset} Update Requirements für ${name}"
    uv sync --package $name
    cd "${base_path}/${name}"
    touch requirements.txt
    rm requirements.txt
    uv pip compile pyproject.toml --output-file requirements.txt
    sed -i '' '/^-e file:\/\//d' requirements.txt
    cd "${START_DIR}"
    ((idx++))
  done
}

# ------------- Ausführung -------------
print_section "Libraries"
run_integrations "lib" "${libraries[@]}"

print_section "Services"
run_integrations "services" "${services[@]}"

print_section "APIs / Prefect-Flows"
run_integrations "api" "${apis[@]}"

echo -e "\n${bold}${magenta}Alle Requirements erfolgreich aktualisiert.${reset}"

