
# Applications Monorepo

This repository is a monorepo that consolidates all core services, shared libraries, and infrastructure for the project.
It is containerized for easy local development and deployment, with consistent tooling across all subprojects.


# Repository Structure

applications/

├── api/                 # Backend API services (e.g., FastAPI or Flask apps)

├── services/            # Independent microservices and background workers

├── lib/                 # Shared Python packages and reusable modules

├── Dockerfile           # Root Docker configuration for the monorepo

├── pyproject.toml       # Project dependencies and build configuration

├── uv.lock              # Dependency lock file (managed by uv / poetry)

├── shell_scripts        # Automatisierte Shell-Skripte zur Verwaltung, Testung und Bereitstellung

└── README.md            # This file



# Setup

Prerequisites
- Python 3.12+
- Docker and Docker Compose
- uv for dependency management

Install uv￼ if you haven’t already:

pip install uv

##  Install Dependencies

Use uv to create and sync the environment:

```bash
uv sync --all-extras --all-packages
```


# shell_scripts

Automatisierte Shell-Skripte zur Verwaltung, Testung und Bereitstellung der Anwendung.
- build_docker.sh – Erzeugt Docker-Container muss aufgerufen werden bevor deployment gestartet werden kann
- end_to_end_test.sh – Führt alle End-to-End-Tests durch.
- integrationtests.sh – Führt alle Integrations-Tests aus.
- unittest.sh – Führt alle Unit-Tests aus.
- update_requirements.sh – Aktualisiert requirements.txt in Projekten für das deployment
- start_sonar.sh - sended programm code an sonarqube

---

# Project Layout Philosophy
This monorepo follows a modular architecture:
- api/ -> All Packages that will be Deployt
- services/ -> Usecase Implmentation
- lib/ -> Libaries

./start_sonar.sh
- Linting, formatting, and type-checking are managed through pyproject.toml configuration.
- Tests can be run using:


# Testing

It exists a domain-test package which contains environment variables definition for testing purposes.
Each package can contain a unittest.sh, integrationstest.sh and end_to_end_test.sh.
It may also contain an end_to_end_test_local.sh or an integrationstest_local.sh.
Those scripts tell the CI/CD and the user how to call the tests of this package.
The end_to_end_test_local.sh contain environment variables to run tests locally they can be updated if needed.

#  Dockerfile Overview

This Dockerfile defines a **modular, multi-stage build** for Python-based API services in the monorepo.

### Build Stages
- **Builder stage** → installs and compiles Python dependencies using `uv`.
- **Runtime stage** → creates a lightweight, secure image for deployment.

### Key Environment Variables
| Variable | Description |
|-----------|-------------|
| `UV_SYSTEM_PYTHON=1` | Installs into the system Python (no virtualenv). |
| `UV_NO_EDITABLE=1` | Disables editable installs for faster builds. |
| `UV_COMPILE_BYTECODE=1` | Precompiles `.pyc` files for faster startup. |
| `PYTHONDONTWRITEBYTECODE=1` | Prevents writing `.pyc` files at runtime. |
| `PYTHONUNBUFFERED=1` | Ensures real-time log output in Docker. |
| `PIP_NO_CACHE_DIR=1` | Disables pip cache to reduce image size. |

### Dependency Management
<!--- Uses **`uv`** (from Astral) for fast, reproducible installs.-->
- `requirements.txt` -> remote dependencies only.  
- Shared local code (`lib`, `services`, `deployment-base`) is copied directly.

### Runtime Setup
- Each API runs in its own directory: `/app/api/${API_FOLDER}/src`.
- `start.sh` defines the service entrypoint.

