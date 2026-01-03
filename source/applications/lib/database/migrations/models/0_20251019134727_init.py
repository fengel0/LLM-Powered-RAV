from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "databasebasemodel" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "examplemodel" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(255) NOT NULL,
    "value" INT NOT NULL
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
    "eJztll1v2jAUhv9KlKtO6qqW0g9N06TQMpVpQNXCNrWqIhObYNWx08RpQYj/Ph/ni4QQDX"
    "ZRNnFBS97zGvs8x7HP3PQEJiw8ukYSjVBIWurTBcn8ZMxNjjyivqw3HRom8v3cAoLyMD0K"
    "J3b4eJl9FMoAOVIZxoiFREmYhE5AfUkFVyqPGANROMpIuZtLEacvEbGlcImckEAFHp+UTD"
    "kmUxKmj/6zPaaE4UICFMPcWrflzNfacNi5/qqdMN3IdgSLPJ67/ZmcCJ7Zo4jiIxgDMZdw"
    "EiBJ8FIasMok9VSKV6wEGUQkWyrOBUzGKGIAw/w8jrgDDAw9E/xpfjE3wOMIDmgpl8Bivo"
    "izynPWqglTXd1Ydwen5x90liKUbqCDmoi50ANV6eKhmmsO0gkIpG0juQpUbQ8iqUeqoRZH"
    "luDiZOhR+mUbyKmQU853WIo5xbcdU1PlgPuczZIK1jAedLrt+4HVvYVMvDB8YRqRNWhDpK"
    "HVWUk9iEsi1PsRv0HZjxg/O4MbAx6Nh36vXS5c5hs8mLAmFElhc/FmI7y02VI1BaOceWEj"
    "H29Z2OLIfWHftbB68XAMjp+X3l8QRsh5fkMBtlcioiHWeVdDXsMrK4gjV1cF2MIqk+uiPU"
    "Wez9ZfJ4V47U1CYuf+EtlfIvtLZGfOmv0l8p8WNll8Xlf9f6WiVxMUVFcz9ZfqqGDtaOU8"
    "NLUZ4a6cqMfG2VlN6X5Yd/roU65SPXpJqBHHFgWEr4hFFQw7XFYjzPwlhmrJO8rQhXk+Nk"
    "6aF83L0/PmpbLotWTKRQ3VTm+ggO1I42KRgDqTqpYlidQ2Kyj37EybsnabVXYpFXssOST+"
    "rj15/w1W15W8kiCEJW1wzi0N2R91GUh4NTaAmNj/TYAnx8d/AFC51gLUsSJANaMkvKKH+n"
    "bf761pjPMhJZBDrhJ8xNSRhwajoXzaTaw1FCHrQp+UwjvoWr/KXK++91vlBgh+oPXe18vi"
    "N4FL29E="
)
