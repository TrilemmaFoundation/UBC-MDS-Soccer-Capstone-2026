#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

cd /home/jovyan/work

echo "Starting Django Server on port 8000..."
python app/manage.py runserver 0.0.0.0:8000 &

echo "Starting Jupyter Lab on port 8888..."
jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --NotebookApp.token=''