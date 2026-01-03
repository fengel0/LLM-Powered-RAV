from typing import Any
from tortoise import fields
from database.session import DatabaseBaseModel


class BasicConfig(DatabaseBaseModel):
    hash = fields.CharField(max_length=256, unique=True)
    config_type = fields.CharField(max_length=64)
    data = fields.JSONField[dict[str, Any]]()


class RagEmbeddingConfig(DatabaseBaseModel):
    hash = fields.CharField(max_length=256, unique=True)
    chunk_size = fields.IntField()
    chunk_overlap = fields.IntField()
    models = fields.JSONField[dict[str, str]]()
    addition_information = fields.JSONField[dict[str, Any]]()


class RagRetrievalConfig(DatabaseBaseModel):
    hash = fields.CharField(max_length=256, unique=True)
    generator_model = fields.CharField(max_length=128)  # e.g. "gpt-4o-mini"
    temp = fields.FloatField()
    prompts = fields.JSONField[dict[str, str]]()
    addition_information = fields.JSONField[dict[str, Any]]()


class RagConfig(DatabaseBaseModel):
    name = fields.CharField(max_length=128, unique=True)
    config_type = fields.CharField(max_length=128)
    hash = fields.CharField(max_length=256, unique=True)

    embedding: fields.ForeignKeyRelation[RagEmbeddingConfig] = fields.ForeignKeyField(
        "models.RagEmbeddingConfig",
        related_name="rag_embedding_config",
        on_delete=fields.RESTRICT,
    )
    retrieval: fields.ForeignKeyRelation[RagRetrievalConfig] = fields.ForeignKeyField(
        "models.RagRetrievalConfig",
        related_name="rag_retrieval_config",
        on_delete=fields.RESTRICT,
    )
