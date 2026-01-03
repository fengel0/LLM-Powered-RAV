from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "databasebasemodel" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
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
    "eJztVmtv2jAU/StRPnVSV7WUPjRNk4BSlWnA1NJtalVFJjaJ1cROY6ctqvjv83VeJDw2oG"
    "hMyocgcu65se85tq/fTJ9j4omDCyTREAnSVE8XIPOT8WYy5BP1ZzFp3zBREOQUABTH01k4"
    "ocPjZ/ShkCGypSKMkCeIgjARdkgDSTlTKIs8D0BuKyJlTg5FjD5FxJLcIdIloQrcPyiYMk"
    "xeiUhfg0drRImHCwVQDGNr3JLjQGO3t52LS82E4YaWzb3IZzk7GEuXs4weRRQfQA7EHMJI"
    "iCTBU2XALJPSUyiesQJkGJFsqjgHMBmhyAMxzM+jiNmggaFHgp/6F3MFeWzOQFrKJGjxNo"
    "mrymvWqAlDta4a13vHpx90lVxIJ9RBrYg50YnKujhV65oLaYcEyraQnBVULQ8iqU/mi1rM"
    "LImLk9SD9M86IqdArnK+wlKZU/nW09RUNeA+88aJg0s0HnS67ZtBo/sdKvGFePK0RI1BGy"
    "I1jY5L6F5sCVf7I95B2UeMn53BlQGvxl2/1y4bl/EGdybMCUWSW4y/WAhPLbYUTYVRzNzY"
    "KMBrGlvMrIz9p8bqycMxOHqc2r8ADJH9+IJCbM1EeI0v4s6G/JpfRhBDjnYFtIVZJu3iUh"
    "3zYl4fiQNLe8coo1T9ouoX1bFS9YvK2K31i2lfXSTcWUdbLgrnu5nySz4qsd7HuZmDb0Pj"
    "fPRqeYQ50lWvtZOTJc79aFzrk0+xSnb0klAtjk0KCmatqyjh15t+b76EWUJJw1umirvH1J"
    "b7hkeFfNjNvbBEQai5sOxT4fa6jV9lTVvf+s3yeoYPNJW+O3KjaZCQ2u68K00SWXqnQTln"
    "Zy41HSZXuNMoy8trMNmfm11mNtzTDozysXZUP6ufH5/WzxVFzyRDzpas0U5v8Ic7zDMJBU"
    "xphVNxKmVbB+O7t7Ttn4ywNVYQMaH/nwIeHR7+hYCKtVBAHSsKqEaUhM25cS1uLlMpVXvZ"
    "yfYy+Q0oZuMe"
)
