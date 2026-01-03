from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "databasebasemodel" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
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
    "eJztmP9P2kAUwP+Vpj+5xBlERLMsSwAxsggYhG3RmOboHXCzvavtdcqM//vuHS2F0iNQs4"
    "ixP6DwvtB7n/fuHveeTZdj4gQHZ0igIQpIXb7aIDK/GM8mQy6Rb/RG+4aJPC8xAYG0cZQX"
    "jszh5c7Nh4HwkS2kwQg5AZEiTALbp56gnEkpCx0HhNyWhpSNE1HI6ENILMHHREyILxW3d1"
    "JMGSZPJIg/evfWiBIHLwVAMTxbyS0x9ZRsMGidnStLeNzQsrkTuiyx9qZiwtncPAwpPgAf"
    "0I0JIz4SBC+EAauMQo9FsxVLgfBDMl8qTgSYjFDoAAzz6yhkNjAw1JPgT+WbuQUemzNAS5"
    "kAFs8vs6iSmJXUhEc1Lmq9vaPqJxUlD8TYV0pFxHxRjjJ1M1fFNQFp+wTCtpBYBSrLgwjq"
    "kmyoy54puDhyPYjf5IEcCxLKSYXFmGN8+ZiaMgbcZc40yuAaxv1Wu3ndr7WvIBI3CB4cha"
    "jWb4KmrKTTlHRvlhIu98dsB82/xPjZ6l8Y8NG46Xaa6cTN7fo3JqwJhYJbjD9aCC8UWyyN"
    "wUjLJLGhh3MmdtmzSOybJlYtHo7B0f3C/gXBENn3j8jH1oqGl7nOdlXllt20BDE0VlkBtr"
    "DKqF1c+fw3USf9SieJVWv7h7dgVHSNomsUh0vRNYrE/reusZjXP8QPAMZKUltMZOdzwSOV"
    "TElrR9M3hud8Lh9WTiqnR9XKqTRRa5lLTtZktNXpq1Mvgab+rxBrTJCfjSy2T/GSS9xRXi"
    "56shzCxmICkI6P19D5UeupfiGtUkXciVTlmW4Z4ZQgf4uii80/asXJ/Sy3fGBJJCET/nSb"
    "6svyzVWJ0XHyZoVYrWxQh9WKtgxBpcEaCBl2LqhzzwJpRqW+olCLOs2CSvMipQXQ7I3vE5"
    "Lxm3ajnR+7vkuoh+XTDahKKy1WpdNw/Us9yQznO1MXnd8n2+omaNO/+hfIVrVgnawb2LnD"
    "keaXU9oxxXMEnjtJdA3Bs+6gftk0rnrNRuu61e0sX6qUEkRSQIWKstesXWqBcrmIfEQjz4"
    "+MdEcmkDXiU3tiZgwgI83+uvkjSmx2ZvyovQplTh8zLkJReb1u7LgLtyD9tFE7vND3GP30"
    "4iPfxmFrbNOoZ+bvE+BhqbRJcy6V9N0ZdMsA5RMFYRmd+ft1t6MZeCcuKZADJgO8xdQW+4"
    "ZDA3G3m1jXUISol+afMby9du1XmmvjsltPDzbhC+pv3V5e/gHNgacF"
)
