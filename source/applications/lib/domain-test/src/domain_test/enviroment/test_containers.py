import os

QDRANT_VERSION = os.getenv("QDRANT_VERSION", "qdrant/qdrant:v1.15.1")
POSTGRES_VERSION = os.getenv("POSTGRES_VERSION", "postgres:16-alpine")
NEO4J_VERSION = os.getenv("NEO4J_VERSION", "neo4j:latest")
MINIO_VERSION = os.getenv("MINIO_VERSION", "minio/minio:RELEASE.2022-12-02T19-19-22Z")
