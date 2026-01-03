# Masterarbeit Deployment Stack

Full Docker-Compose Deployment for RAG, vLLM, Prefect, Storage & Observability
This repository contains a modular Docker-Compose–based deployment designed for a production-grade Retrieval-Augmented Generation (RAG) system. It includes model serving (vLLM), multiple RAG pipeline variants, file indexing services, API endpoints, Prefect orchestration, object storage, databases, and a full observability suite.
The environment is structured into several separate compose files, each responsible for a specific subsystem. All services communicate inside a shared Docker network named dev_env.

---

## Overview of All Components

### Model Serving

vllm.yaml
- Deploys a GPU-accelerated vLLM instance for reranking
- Supports Hugging Face token passing
- Mounted model directory
- Exposed at port 7998
- Uses vllm/vllm-openai with OpenAI-compatible API


### RAG Pipelines

rag_default_instances.yaml
rag_instances.yaml
- Multiple RAG variants:
- Graph-based (directed & undirected)
- Sub-RAG
- Hybrid simple RAG
- All use the rag-prefect:v02 image
- Equipped with:
- Postgres connection
- Neo4j graph DB
- Qdrant vector DB
- vLLM reranker
- OpenTelemetry
- Prefect API integration
- Volumes mount retriever and RAG configurations

---

### RAG UI

rag_ui.yaml
	•	Hosts a RAG API + interactive UI
	•	Exposes port 7600
	•	Loads available LLM models dynamically
	•	Connects to Qdrant, Neo4j, Postgres, vLLM, and embedding services
	•	Stores chat logs via mounted chat_dump/ directory

---

### File Indexing / Embedding Pipeline

index_deployment.yaml
- Runs the File-Index Prefect service
- contains the deployment for file-upload, file-converting and file-embedding
- Watches for new documents in ./files
- Converts, chunks, embeds, and indexes them into Qdrant
- Supports:
- S3 storage
- Postgres metadata
- Configurable embedding prompts and models
- OpenTelemetry instrumentation

---

### Prefect Orchestration

prefect_instance.yaml
- Prefect Server (API + UI)
- Postgres for Prefect storage
- Prometheus exporter to expose flow-run metrics
- Exposes UI on 4200/4201

---

### Storage Layer

storage.yaml
Includes:

MinIO
- S3-compatible object storage
- Web UI on 9001
- Data persisted to ./disks/minio-data-masterarbeit/

Postgres
- Main DB for:
- RAG pipelines
- File indexing
- Data persisted to ./disks/postgres-data-masterarbeit/

Postgres Exporter
- Exposes DB metrics to Prometheus

Adminer
- Simple DB UI at port 9003

---

### Observability Stack

metrik.yaml
Provides full monitoring & tracing:

Prometheus
- Scrapes metrics from all services
- Stores time-series metrics

Grafana
- Dashboards for RAG performance, vLLM GPU metrics, Postgres health, etc.

OpenTelemetry Collector
- Collects and exports traces and metrics

Tempo
- Trace storage (compatible with Grafana Tempo integration)

Loki
- Central log aggregation

cAdvisor & Node Exporter
- Container and host machine metrics
- GPU metrics via dcgm-exporter

This creates a full production observability pipeline.

---

### Helper Scripts

start.sh
Starts all deployments in the correct order.

stop.sh
Stops the stack cleanly.

---

## Folder Structure

.
├── vllm.yaml
├── rag_default_instances.yaml
├── rag_instances.yaml
├── rag_ui.yaml
├── storage.yaml
├── prefect_instance.yaml
├── index_deployment.yaml
├── metrik.yaml
├── start.sh
├── stop.sh
├── config/
├── disks/
└── prompts/

---

## Requirements
- Docker 24+
- NVIDIA Container Toolkit (for GPU inference)
- External datastores configured in .env
- Sufficient GPU memory for vLLM, text-embedding-infereance and file-converter
- Qdrant, Postgres, Neo4j endpoints reachable from containers

---

## Purpose

This deployment was designed for a Master’s thesis focused on:
- Evaluating retrieval methods
- Running multiple RAG variants
- Monitoring LLM behaviour across pipelines
- Collecting metrics and traces for analysis
- Providing an interactive UI and indexing system

