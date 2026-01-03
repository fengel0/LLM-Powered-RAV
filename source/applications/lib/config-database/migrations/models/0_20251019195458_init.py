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
    "config_type" VARCHAR(128) NOT NULL,
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
    "eJztmvFv2jgUx/8VlJ96Uq9qGXTVaToJKNW4tWWidHfaNEUmMcFq4mSO045V/O9nmyQGx8"
    "lBB9e08w+l8PxeYn9eYr+vk0crCF3ox0ddECOnF+Ip8qw/Go8WBgFkX3TNhw0LRJFs5AYK"
    "Jr7wn3BHRzpOYkqAQ1nTFPgxZCYXxg5BEUUhZlac+D43hg5zRNiTpgSjbwm0aehBOoOENX"
    "z5yswIu/A7jLOf0Z09RdB31zqNXH5uYbfpPBK229vB+YXw5Keb2E7oJwGW3tGczkKcuycJ"
    "co94DG/zIIYEUOiuDIP3Mh10Zlr2mBkoSWDeVVcaXDgFic9hWO+mCXY4g4Y4E/9o/WltgY"
    "cx5mgRppzF42I5KjlmYbX4qXrvO6ODN6e/iVGGMfWIaBRErIUIBBQsQwVXCdIhkA/bBrQI"
    "9Jy1UBRAPdT1SAWum4YeZV+eAjkzSMryCsswZ/iextRiY3CH2J+nGaxgPB5c9W/GnauPfC"
    "RBHH/zBaLOuM9bmsI6V6wHy5SE7P5Y3jv5QRp/D8bvG/xn4/Pwuq8mLvcbf7Z4n0BCQxuH"
    "DzZwVy62zJqBYZ4ysUnkPjGx65Emsc+a2LTzMq8zEM+KGe3NANFnM/NX8shg7Wfe+8m8Be"
    "C77UPs0Rn72WyfViTuU2ckJj7mpWTjOm1qLtsWawCXS9cSxBYclbDd4PwfboQ1oKetDXie"
    "tkpx8qZ1mnxhKWL862Z4rceY+Sv8bjEb1xcXOfSw4aOYfq0nzQp6fMhrM0hG7eCq848KtH"
    "c57KpTAz9Al9HlNc/0bmWx5oYJcO4eAHHtQkvYDMt8i01BM1AtAANPsOIj5uNL60G2RgBW"
    "6kFWF8IrbtIVjUWnytLRTd35X5C7mwLSFJCmzjAFpEns3grImqwpI+CVb0DIxso1hADPbD"
    "6YtcOsHfWZYsza8UoTW9h8EP8LGS0XzZn/S9x8OGmebSCWmVepWhZtZvNhr0DNdthPbofB"
    "YAJdl3XC3q6sUeN2WeA860bOf9Yzkh2B7CzwHvhbslPjfhV2BRmiuQyLHC9CApGHP8C5oD"
    "lgnQHY0U2EUkn0s8NJSVFbkNIqJxACHnLhUbjV2IjZOCEVYx6xJX006I0t/ZW5G5yj7HCv"
    "Aad695XgfDaJrF67eq2sucIrRXN+ERn1bNSzUc/1EVlGPb/SxJpH9zt/dD9L8J0dox8a8T"
    "zAtGSyWwtSWPIqoZ53gcfP83vzpPW2dfbmtHXGXERfcsvbCr6D67EWXXgPiQ+iremtxP2q"
    "AGVVtemrDjLCvOxQ9rLDKmE2jyLeRxvhaUgCIPq7Be+yeEO/jP4WjwVXpCXwbKlIpZpYT1"
    "M3PcrFhxH0y1Khe/JX20wUdOVizzpQFd16HaiR5pU6MFe/RgcaHWh0YH3kgtGBrzSxRgfu"
    "WgemQw6Jnb9FuilLTah5mpqDpTDQiMMLPwQl8jALUBhOeUQ9KVZAOx/edi/7jY+jfm9wM0"
    "hr7HzeEI3cxAwoe1jQuVQIRiQMIrqVTlwJMVLFCMU60n+yUJTP2oxQ3I9Q7ECCnJmlEYdp"
    "y2GVIATSpzYisHQvUqsBNRuQaUHzrEXQTnYfyzXfPSSxdtYrr3xWQl5mxdNstzcqJdsVpW"
    "RbrXj4rbEFxNT9ZQI8OT7epGQ8Pi4vGXlb4Y1GCrFGoZavvyshZsndwZK7++Vl8S/vX1Mo"
)
