
export LOG_LEVEL=info
export LOG_SECRETS=False

export POSTGRES_HOST="127.0.0.1"
export POSTGRES_PORT=5432
export POSTGRES_DATABASE="production-db"
export POSTGRES_USER="root"
export POSTGRES_PASSWORD="password-v2"

export UPDATE_MESSAGE="added relevant chunks information to eval"


python src/database_migration/main.py
