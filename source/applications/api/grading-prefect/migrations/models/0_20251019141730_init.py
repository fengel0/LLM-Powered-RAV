from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "basicconfig" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "hash" VARCHAR(256) NOT NULL UNIQUE,
    "config_type" VARCHAR(64) NOT NULL,
    "data" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "databasebasemodel" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
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
