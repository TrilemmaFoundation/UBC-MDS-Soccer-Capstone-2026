# Parquet Output Data Schema

This document specifies the schema for the denormalized Parquet files stored in `parq_output/`. These files are optimized for analytical queries by reducing the need for complex joins.

## 1. `matches.parquet`
**Description**: Consolidated match metadata joined with competition details and team names.
**Grain**: One row per match.

| Column | Type | Description |
| :--- | :--- | :--- |
| `match_id` | INTEGER | Unique match identifier |
| `match_date` | VARCHAR | Date of the match (YYYY-MM-DD) |
| `home_team` | VARCHAR | Name of the home team |
| `away_team` | VARCHAR | Name of the away team |
| `home_score` | INTEGER | Final score for the home team |
| `away_score` | INTEGER | Final score for the away team |
| `competition_name`| VARCHAR | Name of the competition (e.g., "La Liga") |
| `season_name` | VARCHAR | Season name (e.g., "2023/2024") |
| `gender` | VARCHAR | Competition gender |
| `is_youth` | BOOLEAN | Flag for youth competitions |
| `is_international`| BOOLEAN | Flag for international competitions |
| `stadium` | VARCHAR | Name of the stadium |
| `referee` | VARCHAR | Name of the referee |
| `kickoff` | VARCHAR | Match kickoff time |

---

## 2. `events.parquet`
**Description**: Detailed match events (passes, shots, etc.). This table is inherently denormalized with player and team names.
**Grain**: One row per event.

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | VARCHAR | Unique event UUID |
| `match_id` | INTEGER | Reference to `matches.parquet` |
| `period` | INTEGER | Match period (1, 2, 3, 4) |
| `minute` | INTEGER | Minute of the event |
| `second` | INTEGER | Second of the event |
| `type` | VARCHAR | Event type (Pass, Shot, Carry, etc.) |
| `team` | VARCHAR | Team performing the action |
| `player` | VARCHAR | Player performing the action |
| `location_x` | FLOAT | X coordinate (0-120) |
| `location_y` | FLOAT | Y coordinate (0-80) |
| `play_pattern` | VARCHAR | Context of play (e.g., "From Corner") |
| `shot_statsbomb_xg`| FLOAT | Expected goals value (for Shots) |
| `pass_outcome` | VARCHAR | Outcome of the pass (Incomplete, etc.) |

---

## 3. `lineups.parquet`
**Description**: Consolidated player match participation, joining rosters with position history and disciplinary actions.
**Grain**: One row per player-position-match-card combination.

| Column | Type | Description |
| :--- | :--- | :--- |
| `match_id` | INTEGER | Reference to `matches.parquet` |
| `team_name` | VARCHAR | Team name |
| `player_name` | VARCHAR | Player's full name |
| `jersey_number` | INTEGER | Player's jersey number for the match |
| `position_name` | VARCHAR | Name of the position played |
| `from_time` | VARCHAR | Time player started in this position |
| `to_time` | VARCHAR | Time player ended in this position |
| `card_type` | VARCHAR | Type of card received (Yellow, Red) |
| `card_reason` | VARCHAR | Reason for the disciplinary action |

---

## 4. `three_sixty.parquet`
**Description**: High-resolution spatial tracking data for players present at the moment of an event.
**Grain**: One row per tracked player per frame.

| Column | Type | Description |
| :--- | :--- | :--- |
| `event_uuid` | VARCHAR | Reference to `events.parquet` |
| `match_id` | INTEGER | Reference to `matches.parquet` |
| `teammate` | BOOLEAN | Whether the tracked player is a teammate of the actor |
| `actor` | BOOLEAN | Whether the tracked player is the person doing the event |
| `keeper` | BOOLEAN | Whether the tracked player is the goalkeeper |
| `location_x` | FLOAT | X coordinate of the player |
| `location_y` | FLOAT | Y coordinate of the player |
| `visible_area` | VARCHAR | JSON polygon representing the camera's field of view |

---

## 5. `reference.parquet`
**Description**: Consolidated lookup table for all categorical entities (Teams, Players, Positions, etc.).
**Grain**: One row per entity.

| Column | Type | Description |
| :--- | :--- | :--- |
| `table_name` | VARCHAR | Source lookup table (e.g., 'team', 'player', 'position') |
| `id` | INTEGER | Original unique ID from the lookup table |
| `name` | VARCHAR | The human-readable name of the entity |
| `extra_info` | VARCHAR | Additional metadata (e.g., team gender) |

---

## 📜 License & Attribution

- **Data Source**: StatsBomb Open Data
- **License**: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)
- **Usage**: Usage of StatsBomb Open Data is subject to their license (non-commercial use only, attribution required).
- **Citation**: "StatsBomb Open Data"

