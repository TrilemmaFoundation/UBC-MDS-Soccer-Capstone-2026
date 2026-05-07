# Validation Report

**Date:** 2026-05-06  
**Pipeline:** StatsBomb pre-built Parquet -> GCS -> BigQuery  
**Source:** StatsBomb Open Data (provided dataset)

## Row Counts
| Table | Rows |
|-------|------|
| matches | 3,464 |
| events | 12,188,949 |
| lineups | 165,820 |

## Additional Tables
| Table | Notes |
|-------|-------|
| reference | loaded |
| three_sixty | loaded |

## Data Quality Checks
| Check | Result |
|-------|--------|
| Null match_ids in events | 0 |

## Status
All tables loaded into `football-capstone-mds-495504.raw_statsbomb`. 
Tables available for staging by team members.