# aerich_conf.py
import os

# Build the Postgres URL from env vars (with sensible defaults)
DB_URL = (
    f"postgres://{os.getenv('POSTGRES_USER', 'root')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'password')}@"
    f"{os.getenv('POSTGRES_HOST', '127.0.0.1')}:"
    f"{os.getenv('POSTGRES_PORT', '5432')}/"
    f"{os.getenv('POSTGRES_DATABASE', 'production-db')}"
)

# Your models (strings!) + aerich’s own model registry
MODELS = [
    "file_database.model",
    "project_database.model",
    "validation_database.model",
    "config_database.model",
    "hippo_rag_database.model",
    "fact_store_database.model",
    "aerich.models",
]

# Tortoise config Aerich expects
TORTOISE_ORM = {
    "connections": {"default": DB_URL},
    "apps": {
        "models": {
            "models": MODELS,
            "default_connection": "default",
        },
    },
}

# You’ll pass this location to Aerich on init (can also set via env)
MIGRATIONS_LOCATION = os.getenv("MIGRATIONS_LOCATION", "migrations/models")
