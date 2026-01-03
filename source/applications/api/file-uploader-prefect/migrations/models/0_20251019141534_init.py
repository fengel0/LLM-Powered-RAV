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
