# HippoRAG Vector Store Implementation

This package implements the vector store component of the HippoRAG project, which provides vector database functionality for storing and retrieving embeddings in support of retrieval-augmented generation systems.

## Overview

The HippoRAG Vector Store Implementation provides the core functionality for managing vector embeddings using Qdrant as the backend. It enables efficient storage, retrieval, and similarity search of vector data that represents semantic information for large language models.

## Key Features

- **Vector Database Integration**: Uses Qdrant for storing and querying vector data.
- **Embedding Management**: Implements functionality for adding, deleting, and retrieving vector embeddings.
- **Similarity Search**: Supports vector similarity search operations with configurable parameters.
- **Recommendation Queries**: Implements recommendation-based vector search using positive and negative examples.

## Package Structure

- `vector_store.py`: Core implementation of the vector store interface using Qdrant.

## Dependencies

The package requires the following dependencies:

- `qdrant-client`

## Usage

The package is designed to be used as part of the larger HippoRAG system, where it provides the vector database backend for storing and retrieving semantic embeddings.

## References

For more information about the original HippoRAG implementation, visit: [https://github.com/OSU-NLP-Group/HippoRAG](https://github.com/OSU-NLP-Group/HippoRAG) 
