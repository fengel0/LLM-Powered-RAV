from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "databasebasemodel" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
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
    "eJztWW1v0zAQ/itVPg1pTF0pL0IIqdsKFLEWbRkgEIrc2G2tJXZIHNg09b9z5yTNe1jHYO"
    "2WD52S83Px+Tn7Xrwrw5WUOcHeEVFkSgJ2AL9jFBkvO1eGIC6Dh3rQbscgnpdCUAAYR2vR"
    "GI4/dwWfBsontgLAjDgBAxFlge1zT3EpQCpCx0GhtAHIxTwVhYL/CJml5JypBfNh4Nt3EH"
    "NB2QULklfv3Jpx5tDcAjjFubXcUpeelp2djY7eaCRON7Vs6YSuSNHepVpIsYKHIad7qINj"
    "cyaYTxSjmWWglfHSE1FkMQiUH7KVqTQVUDYjoYNkGK9mobCRg46eCf/0Xxtr0GNLgdRyoZ"
    "CLq2W0qnTNWmrgVIfvBic7T5490quUgZr7elAzYiy1IrguUtW8pkTaPsNlW0SVCYXtwRR3"
    "WTWpec0CuTRW3UsebkJyIkhZTndYQnNC3804NWANdCKcy9iDDRybo+PhqTk4/ogrcYPgh6"
    "MpGphDHOlp6WVBuhO5RML5iE7Q6iOdzyPzXQdfO18n42HRcSuc+dVAm0iopCXkL4vQzGZL"
    "pAkxgEwdG3r0ho7Na7aOvVPHauMxDM7OM+cXBVNin/8iPrVKI7In67DlIbfnFiVEkLn2Cn"
    "KLVsbpYijUGJ4OF6E4PzqoSigFRGM2YUIJkNqIpdM2lbSppI04mxBx2lRyTx0bG5/6FSKw"
    "hSG47NXDBfGrPZrVKfgTSLsdD5YC4F860CUXlsPEXC3gtff0aYMHPw1OdAQEVMEt43ioF4"
    "0tc0zqJGZVZZJ6JrM6/4rJWz8L/4bKDalvJh4To+GRtEMXtnl1hVPCNNY4EtCc0Rj9H6qc"
    "KyNdq+EyRTBbGwhiFx4EjgCmWBERLy3+eLL53o7GhsaDlfhuLNvSqS2d2gzblk4P17Gl0o"
    "nTi3VyfQy/nTT/56i3kUk+S59HggBycJlCE9JONYUZlW2plpq2+/CLmdvpCV07x4Mvj3K7"
    "/cNk/DaBZ+g9/DA5KLCqU7aNQQOKDa44C8oEvz+djGsq+0rtAtdnAjj4RrmtdjsOD9T3rW"
    "MeCWhmvkhyIXjgB+qZB7s856bEZ5Rb3q/D+6rCXYPurE7Lch3LG9KSmfpEmBIarup+LA/Y"
    "bWrGotOlJBDc3je3TVNbW29Gbd02TffUsaWmKQrA6/RNqca21Pz55mm/2+tfo3tCWG37FA"
    "3m6x6wY83b5lRjO5m8b3fNA+Zze1FV0cQjjaUMSTEbU8OMRE3nXrntwMvFbRdHkDu9+pjj"
    "LI97+/3n/RdPnvVfAERbspI8b9iFo7H5h5LlJ/PxBn6dg5tReeAnNxsA8WisQWIM304C97"
    "vda+WQbkMK6Zb+YymFYqKiwKpvnDMqbd+8kX3z8jePlRof"
)
