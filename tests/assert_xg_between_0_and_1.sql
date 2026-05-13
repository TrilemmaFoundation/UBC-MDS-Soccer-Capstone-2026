SELECT *
FROM {{ ref('stg_statsbomb__events') }}
WHERE shot_statsbomb_xg IS NOT NULL
  AND (shot_statsbomb_xg < 0 OR shot_statsbomb_xg > 1)