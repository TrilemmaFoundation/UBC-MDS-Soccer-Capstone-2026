# Teem's Technical Brief — Chatbot & Infrastructure

### 1. What It Does and Why

My part covers the **user-facing product** and the **infrastructure/deployment** that securely hosts and automates the entire platform. 

- **Django Chatbot** — An LLM-powered chatbot (using Groq and Llama 3.3) that answers natural language football analytics queries. It utilizes a secure tool-calling architecture to translate questions into BigQuery SQL and format the results.
- **Dashboard Integration** — Seamless integration of the 12-page Looker Studio analytical dashboard directly within the Django web application.
- **Deployment Environment** — A fully containerized stack (Docker Compose) running on a Google Compute Engine (GCE) VM, enforcing least-privilege GCP service accounts for the chatbot and orchestration environments.
- **CI/CD Pipelines** — Automated GitHub Actions workflows for PR validation (dbt tests), Docker image publishing (`arm64`), and secure continuous deployment to the GCE VM.

---

## Part I: Chatbot

### 2. Django Chatbot Architecture

- **LLM Engine & Tool Calling (`llm_engine.py`)**: Uses the Groq API (`llama-3.3-70b-versatile`) to orchestrate a tool-calling loop:
  - **Persona & Context**: The LLM is given a system prompt defining it as an "Elite European Football AI assistant". We pass it strict instructions, critical formatting rules, and the complete database schema (`TABLE_CONTEXT`).
  - **Tool Definition**: We provide a specific function tool called `query_bigquery` defined via a JSON schema. It requires a single parameter: a valid BigQuery Standard SQL `SELECT` statement.
  - **Information Flow**: The user's question triggers the LLM to call the `query_bigquery` tool with its generated SQL. The app executes this SQL, and the raw JSON results are appended to the conversation history as a "tool" role message. Finally, the LLM processes these raw results to construct the final natural language response.
- **Schema Context (`table_schema.py`)**: Provides the LLM with the context of the `dbt_marts` tables so it knows what columns and data are available.
- **Security Check (`is_safe_sql`)**: Blocks any non-SELECT statements to protect the BigQuery database from injection or destructive commands.
- **Fallback & Formatting**: Includes a data-presence check to ensure the LLM formats the results appropriately.
- **Advanced Mode**: A UI toggle that exposes the generated SQL and raw JSON results for debugging purposes.

### 3. Looker Studio Dashboard Integration

- The dashboard is embedded via an iframe inside the Django application (`/dashboard/`).
- It displays 12 pages covering match overviews, clusters, team comparisons, and consistency analysis.

---

## Part II: Infrastructure

### 4. Deployment Environment

- **GCE VM**: The application is deployed on a Google Compute Engine Virtual Machine. This VM is installed with the Docker engine to run the Docker images.
- **Dockerized Services**: The entire stack is containerized using `docker-compose.yml`, which spins up:
  - `django-env` (Chatbot + Dashboard): The Django app folder is embedded directly into this Docker image during the build process.
  - `dagster-env` (Dagster Pipeline UI): The repository folder is mounted as a volume. The entire repository directory is copied to the host VM prior to starting the containers via the `deploy_vm.yml` GitHub workflow action.
  - `jupyter-env` (Databricks/Jupyter Notebooks)
- **Service Accounts**: We enforce least-privilege access using two separate GCP service accounts:
  - **Chatbot SA**: Read-only access to query the final analytics tables. Roles: *BigQuery Data Viewer*, *BigQuery Job User*.
  - **Dagster SA**: Read/write access to run the pipeline, build dbt models, and manage GCS artifacts. Roles: *BigQuery Data Editor*, *BigQuery Job User*, *Storage Admin*, *BigQuery User*.

### 5. CI/CD Pipelines (GitHub Actions)

Our repository relies on three main GitHub Actions workflows for continuous integration and deployment.

**Required GitHub Secrets:** `DOCKER_USERNAME`, `DOCKER_PASSWORD`, `GCE_CHATBOT_SERVICE_ACCOUNT_KEY`, `GCE_DAGSTER_SERVICE_ACCOUNT_KEY` (or `GCE_SERVICE_ACCOUNT_KEY`), `GCE_SSH_PRIVATE_KEY`, `GROQ_API_KEY`
**Required Repository Variables:** `GCE_VM_HOST`, `GCE_VM_USER`, `GCP_PROJECT_ID`

- **dbt Test Workflow (`dbt_test.yml`)**:
  - **Trigger**: PRs touching `models/`, `macros/`, or dbt configuration files.
  - **Secrets/Vars Used**: `GCE_SERVICE_ACCOUNT_KEY`, `GCP_PROJECT_ID`.
  - **What it does**: Authenticates with GCP, creates a temporary BigQuery dataset (e.g., `pr_validation_{PR_NUMBER}`), runs `dbt run` and `dbt test` for staging and intermediate layers, and finally drops the temporary dataset even if the tests fail.
- **Docker CD Workflow (`publish_images.yml`)**:
  - **Trigger**: Manual dispatch or upon successful completion of the "Update conda-lock file" workflow on `main`.
  - **Secrets/Vars Used**: `DOCKER_USERNAME`, `DOCKER_PASSWORD`.
  - **What it does**: Logs into Docker Hub, builds `arm64` Docker images for Django, Jupyter, and Dagster, pushes them to Docker Hub, updates the local `docker-compose.yml` with the newly generated image tags, and commits/pushes this update back to the repository.
- **Deploy CD Workflow (`deploy_vm.yml`)**:
  - **Trigger**: Manual dispatch or upon successful completion of the "Publish Docker Images" workflow on `main` (Depends on the Docker CD Workflow).
  - **Secrets/Vars Used**: `GCE_SSH_PRIVATE_KEY`, `GCE_VM_HOST`, `GCE_VM_USER`, `GROQ_API_KEY`, `GCE_CHATBOT_SERVICE_ACCOUNT_KEY`, `GCE_DAGSTER_SERVICE_ACCOUNT_KEY`.
  - **What it does**: Connects securely to the GCE VM via SSH, archives and securely copies the repository to the VM, injects GitHub secrets into configuration files (like `.env` and service account keys) with secure permissions, shuts down the existing Docker cluster, pulls the latest images, and restarts the containers.

---

### 6. Key Files

| File | Purpose |
|---|---|
| `app/chatbot/llm_engine.py` | Core LLM logic, tool-calling, BigQuery execution, and safety checks |
| `app/chatbot/table_schema.py` | BigQuery schema context fed to the LLM |
| `docker-compose.yml` | Defines all 3 services and their environments |
| `Dockerfile.django` | Dockerfile for the Django chatbot app |
| `.github/workflows/deploy_vm.yml` | Deployment CI/CD pipeline |
| `.github/workflows/dbt_test.yml` | Automated dbt tests for PR validation |

---

### 7. Interview Talking Points

**"Walk me through the Chatbot architecture."**

The chatbot is built using Django and powered by Groq's fast inference engine running the Llama 3.3 model. When a user asks a question, the LLM uses tool-calling to generate a BigQuery SQL query based on the schema context we provide. The system validates that the query is a safe `SELECT` statement, executes it against our analytics marts, and then the LLM formats the results back into a natural language response.

**"How do you ensure the LLM doesn't drop tables or run malicious queries?"**

We use a specialized read-only service account for the chatbot. Additionally, before any SQL is executed, the `is_safe_sql()` function intercepts the query and explicitly blocks non-SELECT statements (like DROP, DELETE, INSERT, UPDATE, MERGE).

**"Walk me through your CI/CD pipeline and deployment strategy."**

We use GitHub Actions for our CI/CD pipeline. For Continuous Integration, any PR modifying our dbt models triggers an automated test that builds the models in a temporary BigQuery dataset to ensure no breaking changes are merged. For deployment, our CD workflows automatically build and publish Docker images to Docker Hub. We deploy to a Google Compute Engine (GCE) VM, and our deployment workflow SSHes into the VM, pulls the latest images, injects necessary secrets securely, and restarts the Docker containers.