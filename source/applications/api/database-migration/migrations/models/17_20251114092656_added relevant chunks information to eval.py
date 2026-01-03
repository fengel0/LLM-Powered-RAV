from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "ratingllm" ADD "relevant_chunks" INT[] NOT NULL;
        ALTER TABLE "ratinguser" ADD "relevant_chunks" INT[] NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "ratingllm" DROP COLUMN "relevant_chunks";
        ALTER TABLE "ratinguser" DROP COLUMN "relevant_chunks";"""


MODELS_STATE = (
    "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"
)
