from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "ragconfig" ADD "config_type" VARCHAR(128) NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "ragconfig" DROP COLUMN "config_type";"""


MODELS_STATE = (
    "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"
    "xWVzq6QLCvyMv1MTdnArF2BbF29eHl4X/TOlTd"
)
