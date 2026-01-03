# HippoRAG Graph Database Implementation

This package implements the graph database component of the HippoRAG project, which is a retrieval-augmented generation system designed for large language models.

## Overview

The HippoRAG Graph Database Implementation provides the core functionality for managing graph data structures using Neo4j as the backend.
It enables efficient storage, retrieval, and traversal of nodes and edges that represent entities and their relationships in the context of retrieval-augmented generation.

## Key Features

- **Graph Database Integration**: Uses Neo4j for storing and querying graph data.
- **Node and Edge Management**: Implements functionality for adding, deleting, and retrieving nodes and edges.
- **PageRank Algorithm**: Includes implementation of personalized PageRank algorithm using GDS (Graph Data Science) library.
- **Graph Projections**: Supports graph projections with weight properties for advanced graph analytics.

## Package Structure

- `graph_implementation.py`: Core implementation of the graph database interface using Neo4j.
- `queries.py`: Contains Cypher queries used for various graph operations.

## Dependencies

The package requires the following dependencies:

- neo4j

## Usage

The package is designed to be used as part of the larger HippoRAG system, where it provides the graph database backend for storing and retrieving knowledge graph information.

## References

For more information about the original HippoRAG implementation, visit: [https://github.com/OSU-NLP-Group/HippoRAG](https://github.com/OSU-NLP-Group/HippoRAG)
