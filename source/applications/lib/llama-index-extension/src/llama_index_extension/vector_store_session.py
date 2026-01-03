from pydantic import BaseModel


class LlamaIndexVectorStoreSessionConfig(BaseModel):
    """
    Configuration for the LlamaIndexVectorStore.
    """

    qdrant_host: str
    qdrant_port: int
    qdrant_api_key: str | None
    qdrant_grpc_port: int = 6334
    qdrant_prefer_grpc: bool = True
    collection: str
    batch_size: int
