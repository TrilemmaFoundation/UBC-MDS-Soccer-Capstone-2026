from dagster import AssetExecutionContext, AssetKey
from dagster_dbt import DbtCliResource, dbt_assets
from pathlib import Path

DBT_MANIFEST_PATH = Path(__file__).parent.parent.parent.parent / "target" / "manifest.json"

@dbt_assets(
    manifest=DBT_MANIFEST_PATH,
    dagster_dbt_translator=None,
)
def football_analytics_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["run"], context=context).stream()
    yield from dbt.cli(["test"], context=context).stream()