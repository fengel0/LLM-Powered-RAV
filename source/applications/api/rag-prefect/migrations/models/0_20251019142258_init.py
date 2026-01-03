from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "databasebasemodel" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "evaluator" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "username" VARCHAR(128) NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS "testsample" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "dataset_id" VARCHAR(128) NOT NULL,
    "question_hash" VARCHAR(256) NOT NULL UNIQUE DEFAULT '',
    "retrival_complexity" DOUBLE PRECISION NOT NULL,
    "question" TEXT NOT NULL,
    "expected_answer" TEXT NOT NULL,
    "expected_facts" TEXT[] NOT NULL,
    "expected_context" TEXT NOT NULL,
    "question_type" VARCHAR(128) NOT NULL,
    "metatdata" JSONB NOT NULL,
    "metadata_filter" JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS "idx_testsample_metatda_da204a" ON "testsample" USING GIN ("metatdata");
CREATE TABLE IF NOT EXISTS "ragsystemanswer" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "answer" TEXT NOT NULL,
    "given_rag_context" TEXT[] NOT NULL,
    "facts" TEXT[] NOT NULL,
    "config_id" VARCHAR(128) NOT NULL,
    "retrieval_latency_ms" DOUBLE PRECISION NOT NULL,
    "generation_latency_ms" DOUBLE PRECISION NOT NULL,
    "number_of_facts_in_context" INT NOT NULL,
    "number_of_facts_in_answer" INT NOT NULL,
    "test_sample_id" UUID NOT NULL REFERENCES "testsample" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "ratingllm" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "rationale" TEXT NOT NULL,
    "config_id" VARCHAR(128) NOT NULL,
    "correctness" DOUBLE PRECISION NOT NULL,
    "completeness" BOOL[] NOT NULL,
    "completeness_in_data" BOOL[] NOT NULL,
    "system_answer_id" UUID NOT NULL REFERENCES "ragsystemanswer" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "ratinguser" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "rationale" TEXT NOT NULL,
    "creator" VARCHAR(128) NOT NULL,
    "correctness" DOUBLE PRECISION NOT NULL,
    "completeness" BOOL[] NOT NULL,
    "completeness_in_data" BOOL[] NOT NULL,
    "system_answer_id" UUID NOT NULL REFERENCES "ragsystemanswer" ("id") ON DELETE CASCADE
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
CREATE TABLE IF NOT EXISTS "project" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "version" INT NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "year" INT NOT NULL,
    "address__country" VARCHAR(64),
    "address__state" VARCHAR(64),
    "address__county" VARCHAR(64),
    "address__city" VARCHAR(64),
    "address__street" VARCHAR(128),
    "address__zip_code" VARCHAR(16),
    "address__lat" DOUBLE PRECISION,
    "address__long" DOUBLE PRECISION
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
CREATE TABLE IF NOT EXISTS "facts" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "hash" VARCHAR(255) NOT NULL,
    "facts" JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS "idx_facts_hash_193647" ON "facts" ("hash");
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
