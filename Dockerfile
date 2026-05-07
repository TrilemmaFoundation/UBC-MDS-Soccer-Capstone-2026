# The base image is multi-arch, so it will automatically pull the ARM version on an ARM runner
FROM quay.io/jupyter/minimal-notebook:afe30f0c9ad8

# 1. Update the lock file name to the ARM version
COPY conda-linux-aarch64.lock /tmp/conda-linux-aarch64.lock

USER root

# install lmodern for Quarto PDF rendering
RUN apt-get update \
    && apt-get install -y lmodern texlive texlive-luatex \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

USER $NB_UID

# 2. Update the conda command to point to the ARM lock file
RUN conda update --quiet --file /tmp/conda-linux-aarch64.lock \
    && conda clean --all -y -f \
    && fix-permissions "${CONDA_DIR}" \
    && fix-permissions "/home/${NB_USER}"

RUN pip install \
    duckdb \

# Switch to root to copy the script and set permissions
# USER root

# Switch back to the default safe user for Jupyter stacks
USER $NB_UID

# Optional: If you want the container to start the Django web app by default 
# instead of Jupyter, uncomment the CMD line below:
# CMD ["python", "app/manage.py", "runserver", "0.0.0.0:8000"]