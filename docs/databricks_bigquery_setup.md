# Databricks Free Edition + BigQuery Setup

This guide documents the team setup for querying BigQuery data from Databricks.

## Prerequisites

- Databricks Free Edition account and workspace
- GCP service account key JSON shared by `@quandothoang`
- GCP project ID: `football-capstone-mds-495504`
- BigQuery dataset: `raw_statsbomb`

## 1. Create BigQuery connection in Databricks

1. In Databricks, open `Catalog`.
2. Create a new `Connection`.
3. Set:
   - **Connection type**: `Google BigQuery`
   - **Connection name**: `bq_raw_statsbomb_sa`
4. In authentication:
   - Paste the full service account key into **Google service account key json**.
   - Set **Project id** to `football-capstone-mds-495504`.
5. Create the connection.

## 2. Create foreign catalog

During catalog setup, use:

- **Catalog name**: `bq_raw_statsbomb_sa_catalog`
- **Connection**: `bq_raw_statsbomb_sa`
- **Data Project Id**: `football-capstone-mds-495504`
- **Materialization Dataset**: `databricks_materialization`
- **BIG_NUMERIC Data Scale**: `38`

Run **Test connection**. Once it succeeds, create/save the catalog.

## 3. Verify from a Databricks notebook

Create a SQL notebook and run:

```sql
SELECT * FROM bq_raw_statsbomb_sa_catalog.raw_statsbomb.matches LIMIT 10;
```

Expected result: query returns 10 rows from `matches`.

Optional checks:

```sql
SHOW CATALOGS;
SHOW SCHEMAS IN bq_raw_statsbomb_sa_catalog;
SHOW TABLES IN bq_raw_statsbomb_sa_catalog.raw_statsbomb;
```

## 4. Security notes

- Do not commit `service-account-key.json` to git.
- Do not paste credentials into screenshots, PR descriptions, or chat.
- Keep credentials only in approved secure storage (team drive/Databricks connection settings).

## 5. Task completion checklist

- [x] Databricks Free Edition account created
- [x] Workspace created
- [x] BigQuery connector configured with service account JSON
- [x] Verification query executed successfully from Databricks notebook
- [x] Setup steps documented for the team
