# Database Package  

## Overview  
A lightweight Python package that provides a **generic database access layer** built on top of **Tortoise‑ORM**. It abstracts common CRUD operations behind a type‑safe, asynchronous API and includes built‑in support for PostgreSQL, schema migrations (Aerich), and OpenTelemetry tracing. The design encourages reuse across projects by letting you define your own models once and obtain a ready‑to‑use data‑access object.  

## Key Features  
- **Generic `BaseDatabase` class** – works with any model that inherits from `DatabaseBaseModel`.  
- **Async PostgreSQL session** managed by `PostgresSession` with automatic connection handling.  
- **Automatic migrations** via Aerich, triggered during session startup.  
- **OpenTelemetry integration** for tracing database calls.  
- **Pydantic‑based configuration** (`DatabaseConfig`) for clear, validated settings.  
- **Test‑container ready** – integration tests run against an isolated PostgreSQL container.  

## Installation  

```bash
pip install database
```

The package depends on:  

- `pydantic==2.11.10`  
- `asyncpg==0.30.0`  
- `tortoise-orm==0.25.1`  
- `aerich==0.9.2`  

(see `pyproject.toml` for the full list)【3】  

## Configuration  

Create a `DatabaseConfig` instance with the required connection details (host, port, database name, username, password). The `migration_location` defaults to `./migrations` but can be overridden.  

## Session Management  

`PostgresSession` is a singleton that:  

- Stores the configuration and model modules.  
- Initializes Tortoise‑ORM with a PostgreSQL DSN.  
- Executes a simple health‑check query (`SELECT 1;`).  
- Provides a graceful shutdown method to close all connections.  

The session also sets up an OpenTelemetry tracer named `"DatabaseSession"` for all database operations【1】.  

## Generic Database Access  

`BaseDatabase[T]` is a generic wrapper where `T` must inherit from `DatabaseBaseModel`. It supplies:  

- Standard CRUD methods (create, read, update, delete).  
- Query execution utilities that return typed model instances.  
- Integrated tracing via a dedicated tracer (`MongoDatabase-{ModelClass}` placeholder).  

The model base class supplies common fields (`id`, `created_at`, `updated_at`) and a helper to retrieve the string representation of the primary key【1】.  

## Testing  

The test suite uses **Testcontainers** to spin up an ephemeral PostgreSQL instance, ensuring that database interactions are exercised against a real server. Example test flow:  

1. Start a `PostgresContainer` with test credentials.  
2. Initialise `PostgresSession` pointing at the container.  
3. Run a series of assertions against an `ExampleModelDatabase` derived from `BaseDatabase`.  

This approach guarantees isolation and reproducibility of integration tests【4】.  

