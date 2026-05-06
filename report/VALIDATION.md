# Validation Report

**Date:** 2026-05-05  
**Pipeline:** StatsBomb -> Parquet -> GCS -> BigQuery  
**Competition:** La Liga, Season 2020/2021 (competition_id=11, season_id=90)

## Row Counts
| Table | Rows |
|-------|------|
| matches | 35 |
| events | 139,030 |
| lineups | 1,542 |

## Data Quality Checks
| Check | Result |
|-------|--------|
| Null match_ids in events | 0 |

## Status
All checks passed. Tables available in `football-capstone-mds-495504.raw_statsbomb`.