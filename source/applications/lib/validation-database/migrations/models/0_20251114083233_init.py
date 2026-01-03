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
    "relevant_chunks" INT[] NOT NULL,
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
    "relevant_chunks" INT[] NOT NULL,
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
    "5tK12EwRBxzuXinJsxkbl2Dbl2/enl+X9pF9gC"
)
