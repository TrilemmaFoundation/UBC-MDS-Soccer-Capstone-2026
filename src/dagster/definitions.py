from dagster import Definitions, define_asset_job, AssetSelection
from dagster_dbt import DbtCliResource
from src.dagster.assets.ingestion import raw_statsbomb, raw_polymarket
from src.dagster.assets.dbt_assets import football_analytics_dbt_assets
from pathlib import Path

DBT_PROJECT_DIR = Path(__file__).parent.parent.parent

full_pipeline_job = define_asset_job(
    name="full_pipeline",
    selection=AssetSelection.assets(raw_statsbomb, raw_polymarket) 
              | AssetSelection.all(),
)

defs = Definitions(
    assets=[raw_statsbomb, raw_polymarket, football_analytics_dbt_assets],
    jobs=[full_pipeline_job],
    resources={
        "dbt": DbtCliResource(project_dir=str(DBT_PROJECT_DIR)),
    },
)