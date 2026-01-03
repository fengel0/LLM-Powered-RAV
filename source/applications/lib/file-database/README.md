# File Database Package
This package provides a database abstraction layer for managing file metadata and related data using Tortoise ORM.

## Features
- File and page metadata management
- Fragment support for file pages
- PostgreSQL database integration
- Integration tests

## Installation
Install the package using uv:

```bash
uv sync
```

## Usage

## Running Tests
To run the integration tests, execute:
```bash
./integrationstest.sh
```

or
```bash
pytest tests/integration_test.py
```

## Project Structure

- `src/file_database/` - Main source code directory
  - `model.py` - Database models
  - `file_db_implementation.py` - Database implementation logic
- `tests/` - Test files
- `migrations/` - Database migration files

## Dependencies

- Tortoise ORM
- PostgreSQL
- uv for package management
