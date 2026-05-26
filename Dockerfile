# Use a multi-arch Jupyter base image
FROM quay.io/jupyter/minimal-notebook:afe30f0c9ad8

# 1. ROOT ACTIONS: System installs and file permissions
USER root

# Install system dependencies (LaTeX for Quarto and netcat for networking checks)
RUN apt-get update \
    && apt-get install -y lmodern texlive texlive-luatex netcat-openbsd \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy configuration and script files
COPY conda-linux-aarch64.lock /tmp/conda-linux-aarch64.lock
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

# Set execution permissions for the entrypoint script
RUN chmod +x /usr/local/bin/entrypoint.sh

# 2. USER ACTIONS: Python environment management
# Switch to the default notebook user for all package installations
USER $NB_UID
WORKDIR /home/${NB_USER}/work

# Update Conda environment using the ARM lock file (Fixed line continuation syntax)
RUN conda update --quiet --file /tmp/conda-linux-aarch64.lock \
    && conda clean --all -y -f \
    && fix-permissions "${CONDA_DIR}" \
    && fix-permissions "/home/${NB_USER}"

# Install pip packages
RUN pip install --no-cache-dir \
    duckdb \
    statsbombpy \
    google-cloud-storage \
    google-cloud-bigquery \
    google-cloud-bigquery-storage \
    python-dotenv \
    dbt-core \
    dbt-bigquery \
    dagster \
    dagster-webserver \
    dagster-dbt \
    dagster-gcp \
    django \
    djangorestframework \
    django-htmx \
    groq \
    xgboost \
    plotly

COPY --chown=${NB_UID}:${NB_GID} app/ /home/${NB_USER}/work/app/

# Final container execution setting
# ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]