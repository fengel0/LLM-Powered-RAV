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
    "/lYBMi"
)
