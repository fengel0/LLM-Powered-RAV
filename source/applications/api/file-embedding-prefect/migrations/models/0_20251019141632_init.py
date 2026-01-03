from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "databasebasemodel" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "file" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "filepath" VARCHAR(256) NOT NULL,
    "filename" VARCHAR(256) NOT NULL,
    "bucket" VARCHAR(256) NOT NULL,
    "metadata_project_id" VARCHAR(256) NOT NULL,
    "metadata_project_year" INT NOT NULL,
    "metadata_file_creation" TIMESTAMPTZ NOT NULL,
    "metadata_file_updated" TIMESTAMPTZ NOT NULL,
    "metadata_version" INT NOT NULL,
    "metatdata_other" JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS "idx_file_metatda_a8cb12" ON "file" USING GIN ("metatdata_other");
CREATE TABLE IF NOT EXISTS "filepage" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "bucket" VARCHAR(256) NOT NULL,
    "page_number" INT NOT NULL,
    "metadata__project_id" VARCHAR(256) NOT NULL,
    "metadata__project_year" INT NOT NULL,
    "metadata__file_creation" TIMESTAMPTZ NOT NULL,
    "metadata__file_updated" TIMESTAMPTZ NOT NULL,
    "metadata__version" INT NOT NULL,
    "file_id" UUID NOT NULL REFERENCES "file" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "pagefragement" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "fragement_type" VARCHAR(16) NOT NULL,
    "storage_filename" VARCHAR(256) NOT NULL,
    "fragement_number" INT NOT NULL,
    "page_id" UUID NOT NULL REFERENCES "filepage" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "entnodechunkdb" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "ent_node" VARCHAR(255) NOT NULL,
    "chunk_id" VARCHAR(255) NOT NULL
);
CREATE INDEX IF NOT EXISTS "idx_entnodechun_ent_nod_0fd36d" ON "entnodechunkdb" ("ent_node");
CREATE TABLE IF NOT EXISTS "openiedocumentdb" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "idx" VARCHAR(255) NOT NULL UNIQUE,
    "passage" TEXT NOT NULL,
    "extracted_entities" JSONB NOT NULL,
    "extracted_triples" JSONB NOT NULL,
    "metadata" JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS "idx_openiedocum_idx_4510b1" ON "openiedocumentdb" ("idx");
CREATE INDEX IF NOT EXISTS "idx_openiedocum_metadat_663224" ON "openiedocumentdb" USING GIN ("metadata");
CREATE TABLE IF NOT EXISTS "tripletodocdb" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "triple" VARCHAR(1024) NOT NULL,
    "doc_id" VARCHAR(255) NOT NULL
);
CREATE TABLE IF NOT EXISTS "basicconfig" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "hash" VARCHAR(256) NOT NULL UNIQUE,
    "config_type" VARCHAR(64) NOT NULL,
    "data" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "ragembeddingconfig" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "hash" VARCHAR(256) NOT NULL UNIQUE,
    "chunk_size" INT NOT NULL,
    "chunk_overlap" INT NOT NULL,
    "models" JSONB NOT NULL,
    "addition_information" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "ragretrievalconfig" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "hash" VARCHAR(256) NOT NULL UNIQUE,
    "generator_model" VARCHAR(128) NOT NULL,
    "temp" DOUBLE PRECISION NOT NULL,
    "prompts" JSONB NOT NULL,
    "addition_information" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "ragconfig" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(128) NOT NULL UNIQUE,
    "hash" VARCHAR(256) NOT NULL UNIQUE,
    "embedding_id" UUID NOT NULL REFERENCES "ragembeddingconfig" ("id") ON DELETE RESTRICT,
    "retrieval_id" UUID NOT NULL REFERENCES "ragretrievalconfig" ("id") ON DELETE RESTRICT
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
)
