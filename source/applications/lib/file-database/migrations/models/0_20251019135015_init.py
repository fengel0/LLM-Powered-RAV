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
    "eJztWm1v2zYQ/iuGPqVAFsRukhbFUMB58ep1cYrE2YYWhUBLtKxFolSJamIE/u/jUa8WRc"
    "VvQaWEHxLYxzuR95zIu3vMR831TOyEB+eIogkK8Sn7uwSR9qHzqBHkYvZBrrTf0ZDv5yog"
    "YDoOtzITdfhzM/VJSANkUKYwRU6ImcjEoRHYPrU9wqQkchwQegZTtImViyJi/4iwTj0L0x"
    "kO2MC370xsExM/4DD96t/pUxs75pIDtglzc7lO5z6X3d4OzwdcE6ab6IbnRC7Jtf05nXkk"
    "U48i2zwAGxizMMEBotgsuAGrTFxPRfGKmYAGEc6WauYCE09R5AAY2u/TiBiAQYfPBP+OPm"
    "prwGN4BKC1CQUsHhexV7nPXKrBVGef+td7b0/ecC+9kFoBH+SIaAtuyEIXm3JccyCNAIPb"
    "OqIioOz1wNR2cTWoy5YlcM3E9CD9sAnIqSBHOX/DUphT+DbDVGM+mFfEmScRrMF4PLy8uB"
    "n3L7+AJ24Y/nA4RP3xBYz0uHReku7FIfHY/oh3UPaQzj/D8acOfO18vRpdlAOX6Y2/arAm"
    "FFFPJ969jszCy5ZKU2CYZh7YyDc3DOyypQrsLw0sXzwcg9O7wv4FwQQZd/coMHVhxOt5Ml"
    "1xyO25ZQkiyOJRAWxhlUm6GNjcWSGNcHlt5pimGs+ZLB613A/NxRRRfup5XB108YPPwhCy"
    "mTJfE0+SOdKX/I/hSOP6bLHwXVuoRKQSkTqvVCJ6vYFNFp/HFc50H9GZGNWzGQqqI1q0Kc"
    "WTgdbQCLroQXcwsdiyP3R6xyc1Ify7f82PQKZVissoGerFYwsBSv55TShTGwVlBuUkMu5w"
    "xUkjBzK3UDDmlR0rn3iq9gPvP2xQvarOkWMqMVcAywGeYxSIEA8JXRHh1L6EMXOpoRhbMM"
    "9vve7Ru6P3b0+O3jMVvpZM8q4G9eFoLAMUDkad14SwojVLDvlT2ll+tKTcSN2uLSSXY5MU"
    "h9sFuPAQFd/GxPcnDsLKvfv0aVgwfc0HYZH5EFD88+ZqJIexZFpC8ZYw776ZtkH3O44d0u"
    "/NxLQGMPB+aUekaXrvsv9vOYOf/XV1Wn7V4QGnDPM1SLk8OD6ycCiG5DQxG3y+xo4s5RTY"
    "ti/sMY1GPpdqBQ7zOYlJDomEnEzhqico/VRL/aKliMS2FgQvhm9SROILDaxAJCrKZieMAq"
    "QvnUTupKrmk1bOJavXXDTzjLIt4aUYrycZr60pL8V5CZDuhvRSrFeDWZHd0F6K92pwhLcg"
    "vhTzFTfxlXlb3kcXTHbZTP/SDfBE7yzwVssAiugNvADbFvmM5xzDIVsHIkbVD8+l+2CNRU"
    "1gp5g4QPcZK1N8LZh7zClM4wKwf3PWP7+I74M9xfVNA2S5GGYWIF2H7wPyasAeheFZ7YL1"
    "WUm/ZVwqmD8BODn9B13QdElVcYCKA2xrcfRiqCLFAb7QwIqXCdPDNw6JENuae3CCZTs5l+"
    "4qlEtXzrh0BcIlpB5go29yu7DKtp24Ps+FzeylW5twrTJ9rQ0bJ5/XK3oKJqph09KfrHfQ"
    "sLXvSsF+qWkrvBrrNm3P2af0cWAbM62iQUlG9us6E5TrNKYlkZ5tlfuy4jRLorddK9KEo0"
    "zegUipPHnOlTN4rUm1xyul2uOaVHtcTrWwNdYAMVFvJ4Ddw8NVisDDQ3kVCGPLALIZacJq"
    "rHoPsGCi7v+Vs/IG9/92n14W/wNHwjm7"
)
