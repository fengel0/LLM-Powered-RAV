# llama-index-extension

This package extends the functionality of LlamaIndex to provide additional features for building and managing RAG (Retrieval-Augmented Generation) systems.
It integrates with Qdrant for vector storage and uses custom embedding and reranking components.

## Features

- **Custom Embedding**: Implements a custom embedding class that integrates with external embedding clients.
- **Custom Reranker**: Provides a custom reranker client for re-ranking nodes based on relevance.
- **LLM Integration**: Supports integration with various LLMs, including a mock LLM for testing purposes.
- **Vector Store Session Management**: Manages Qdrant vector store sessions for efficient storage and retrieval.
- **Simple Builder**: Offers a simple builder for creating chat engines with configurable parameters.
- **Sub-Question Builder**: Enables the creation of sub-question engines for complex query processing.
- **Logging**: Integrates with OpenTelemetry for logging and tracing.

## Installation

To install the package using `uv`, run:

```bash
uv sync
```

## Usage

### Building a Simple Chat Engine

```python
from llama_index_extension.simple_builder import LlamaIndexSimpleBuilder
from llama_index_extension.build_components import LLamaIndexHolder
from llama_index_extension.embedding import CustomEmbedding
from llama_index_extension.reranker import CustomRerankerClient

# Configure the builder
builder_config = LlamaIndexSimpleBuilderConfig(
    reranker=AsyncRerankerClient(),
    embedding=EmbeddClient(),
    top_n_count_reranker=5,
    top_n_count_dens=10,
    top_n_count_sparse=10,
    context_window=4096,
    llm_model="gpt-4",
    temperatur=0.7,
    sparse_model="Qdrant/bm25",
)

# Build the chat engine
builder = LlamaIndexSimpleBuilder(builder_config)
chat_engine = builder.build_chat_engine()
```

### Building a Sub-Question Engine

```python
from llama_index_extension.sub_question_builder import LlamaIndexSubQuestionBuilder
from llama_index_extension.build_components import LLamaIndexHolder
from llama_index_extension.embedding import CustomEmbedding
from llama_index_extension.reranker import CustomRerankerClient

# Configure the builder
builder_config = LlamaIndexSubQuestionBuilderConfig(
    reranker=AsyncRerankerClient(),
    embedding=EmbeddClient(),
    top_n_count_dens=10,
    top_n_count_sparse=10,
    top_n_count_reranker=5,
    context_window=4096,
    llm_model="gpt-4",
    temperatur=0.7,
    sparse_model="Qdrant/bm25",
)

# Build the sub-question engine
builder = LlamaIndexSubQuestionBuilder(builder_config)
sub_question_engine = builder.build_chat_engine()

```

## Components

- `build_components.py`: Contains components for managing LlamaIndex configurations and vector stores [1].
- `embedding.py`: Implements custom embedding classes for integrating with external embedding clients [2].
- `llm.py`: Provides LLM integration and utilities for handling chat and completion responses [3].
- `logging.py`: Integrates with OpenTelemetry for logging and tracing [4].
- `mock_llm.py`: Implements a mock LLM for testing purposes [5].
- `prompts.py`: Defines default prompts for various LlamaIndex components [6].
- `reranker.py`: Implements custom reranker clients for re-ranking nodes [7].
- `simple_builder.py`: Provides a simple builder for creating chat engines [8].
- `sub_question_builder.py`: Enables the creation of sub-question engines [9].
- `vector_store_session.py`: Manages Qdrant vector store sessions [10].

