#!/usr/bin/env bash
# Build Docker-Images für alle Python-APIs/Prefect-Flows sowie das Chatbot-UI
# -------------------------------------------------------------------------
set -euo pipefail

START_DIR="$(pwd)"

# ------------ Zu bauende Images ------------
images=(
  #database-migration
  #dataset-file-loader-prefect
  #dataset-loader-prefect
  #file-converter-api
  #file-converter-prefect
  #file-embedding-prefect
  #file-uploader-prefect
  #grading-prefect
  #graph-view
  rag-prefect
  simple-rag-api
  #trigger-evaluation-prefect
)

# ------------ Farben & Helfer ------------
bold=$(tput bold 2>/dev/null || true)
blue=$(tput setaf 4 2>/dev/null || true)
green=$(tput setaf 2 2>/dev/null || true)
reset=$(tput sgr0 2>/dev/null || true)

print_header() {
  echo -e "\n${bold}${blue}=== $1 ===${reset}"
}

build_image_python() {
  local name="$1"
  pushd "${START_DIR}" >/dev/null
    docker build --build-arg API_FOLDER="${name}" -t "${name}:v02" -f Dockerfile .
  popd >/dev/null
}


# ------------ Build-Schleife ------------
print_header "Docker-Builds für Python-APIs & Prefect-Flows"

total=${#images[@]}
for i in "${!images[@]}"; do
  idx=$(( i + 1 ))
  img="${images[i]}"
  echo -e "${bold}${green}[${idx}/${total}]${reset} Baue ${img} …"
  build_image_python "${img}"
done



#docker build -t "file-index-prefect:v02" -f index.Dockerfile .
