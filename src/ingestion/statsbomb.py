import gc
import os
import re
import pandas as pd
from statsbombpy import sb
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = "data/parquet"
os.makedirs(f"{OUTPUT_DIR}/matches", exist_ok=True)
os.makedirs(f"{OUTPUT_DIR}/events", exist_ok=True)
os.makedirs(f"{OUTPUT_DIR}/lineups", exist_ok=True)

# Number of matches to hold in memory at one time while fetching events.
# StatsBomb open data has ~3 464 matches with ~12.2 M event rows total.
# Loading everything at once requires 5–15 GB of RAM; batching keeps each
# iteration well under 1 GB so the pipeline runs inside the Docker memory limit.
EVENTS_BATCH_SIZE = 50

# statsbombpy reads SB_USERNAME and SB_PASSWORD from the environment automatically.
# If both are set, the paid API is used (full historical data).
# If either is missing, the library falls back to StatsBomb open data (free, GitHub-hosted).
_sb_user = os.getenv("SB_USERNAME")
_sb_pass = os.getenv("SB_PASSWORD")
if _sb_user and _sb_pass:
    print("StatsBomb: using authenticated API (paid data)")
else:
    print("StatsBomb: SB_USERNAME/SB_PASSWORD not set — using open data (free)")

# Competition names must match StatsBomb's exact spelling (case-sensitive).
# "Indian Super league" uses lowercase 'l' as returned by the StatsBomb API.
TARGET_COMPETITIONS = [
    "La Liga",
    "Ligue 1",
    "Premier League",
    "Serie A",
    "1. Bundesliga",
    "Indian Super league",
    "Champions League",
    "Major League Soccer",
    "Copa del Rey",
    "UEFA Europa League",
    "Liga Profesional",
    "North American League",
    "FIFA World Cup",
    "UEFA Euro",
    "African Cup of Nations",
    "Copa America",
]

def clean_column_names(df):
    df.columns = [
        re.sub(r'[.\s]', '_', col).replace('-', '_')
        for col in df.columns
    ]
    df.columns = [f"col_{col}" if col[0].isdigit() else col for col in df.columns]
    return df

def extract_matches():
    print("Fetching all competitions...")
    all_comps = sb.competitions()

    # filter: men's senior, from 1970 onwards, target competitions only
    filtered = all_comps[
        (all_comps["competition_name"].isin(TARGET_COMPETITIONS)) &
        (all_comps["competition_gender"] == "male") &
        (all_comps["season_name"].apply(lambda x: int(str(x)[:4]) >= 1970))
    ]

    print(f"Found {len(filtered)} competition-seasons to extract")

    if len(filtered) == 0:
        available = sorted(all_comps["competition_name"].unique().tolist())
        raise ValueError(
            f"No competition-seasons matched TARGET_COMPETITIONS in the available data.\n"
            f"Available competitions from the API: {available}\n"
            f"Check competition name spelling (case-sensitive) in TARGET_COMPETITIONS."
        )

    all_matches = []
    for _, row in filtered.iterrows():
        comp_id = row["competition_id"]
        season_id = row["season_id"]
        comp_name = row["competition_name"]
        season_name = row["season_name"]
        print(f"  Matches: {comp_name} {season_name}")
        try:
            matches = sb.matches(competition_id=comp_id, season_id=season_id)
            all_matches.append(matches)
        except Exception as e:
            print(f"  ERROR: {comp_name} {season_name} -- {e}")

    if not all_matches:
        raise ValueError(
            "No matches were fetched — all competition/season requests failed or returned nothing. "
            "If using open data, check that TARGET_COMPETITIONS names match the StatsBomb API exactly. "
            "If using the paid API, verify SB_USERNAME and SB_PASSWORD are set correctly in .env."
        )

    df = pd.concat(all_matches, ignore_index=True)
    df = pd.json_normalize(df.to_dict(orient="records"))
    # cast mixed-type columns to string to avoid pyarrow errors
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str)
    df = clean_column_names(df)
    df.to_parquet(f"{OUTPUT_DIR}/matches/matches.parquet", index=False)
    print(f"Saved {len(df)} matches total")
    return df["match_id"].tolist()

def extract_events(match_ids):
    """Extract events in batches to avoid OOM on large datasets.

    StatsBomb open data contains ~12.2 M event rows across ~3 464 matches.
    Loading everything into a single DataFrame before writing requires 5–15 GB of
    RAM and will crash inside a constrained Docker container.  Instead we process
    EVENTS_BATCH_SIZE matches at a time, write each batch as a separate Parquet
    part file (events/part_0000.parquet, part_0001.parquet …), and then let
    BigQuery load them via a wildcard URI.
    """
    print(
        f"Extracting events for {len(match_ids)} matches "
        f"(batch_size={EVENTS_BATCH_SIZE})..."
    )

    events_dir = f"{OUTPUT_DIR}/events"
    # Remove stale part files from any previous run
    for fname in os.listdir(events_dir):
        if fname.endswith(".parquet"):
            os.remove(os.path.join(events_dir, fname))

    total_events = 0
    part = 0
    any_fetched = False

    for batch_start in range(0, len(match_ids), EVENTS_BATCH_SIZE):
        batch = match_ids[batch_start : batch_start + EVENTS_BATCH_SIZE]
        batch_events = []

        for i, match_id in enumerate(batch):
            global_i = batch_start + i
            print(f"  Events {global_i + 1}/{len(match_ids)} match_id={match_id}")
            try:
                events = sb.events(match_id=match_id)
                events["match_id"] = match_id
                batch_events.append(events)
            except Exception as e:
                print(f"  ERROR match_id={match_id} -- {e}")

        if not batch_events:
            print(f"  Batch {part}: no events fetched, skipping")
            continue

        df = pd.concat(batch_events, ignore_index=True)
        del batch_events  # release per-match frames before column processing

        for col in df.columns:
            if df[col].dtype == object:
                try:
                    sample = df[col].dropna().iloc[0]
                    if isinstance(sample, dict):
                        normalized = pd.json_normalize(
                            df[col].apply(lambda x: x if isinstance(x, dict) else {})
                        )
                        normalized.columns = [f"{col}.{c}" for c in normalized.columns]
                        df = pd.concat([df.drop(columns=[col]), normalized], axis=1)
                except (IndexError, Exception):
                    pass

        # Cast object columns to string to avoid pyarrow schema issues
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str)

        df = clean_column_names(df)
        part_path = os.path.join(events_dir, f"part_{part:04d}.parquet")
        df.to_parquet(part_path, index=False)
        total_events += len(df)
        print(f"  Batch {part}: wrote {len(df):,} rows -> {part_path}")
        part += 1
        any_fetched = True

        del df
        gc.collect()  # explicitly free memory between batches

    if not any_fetched:
        raise ValueError(
            "No events were fetched — all match event requests failed or returned nothing. "
            "Check the match IDs returned by extract_matches() and your StatsBomb credentials."
        )

    print(f"Saved {total_events:,} events total across {part} part file(s)")

def extract_lineups(match_ids):
    print(f"Extracting lineups for {len(match_ids)} matches...")
    all_lineups = []
    for i, match_id in enumerate(match_ids):
        print(f"  Lineups {i+1}/{len(match_ids)} match_id={match_id}")
        try:
            lineups = sb.lineups(match_id=match_id)
            for team_name, lineup_df in lineups.items():
                lineup_df["match_id"] = match_id
                lineup_df["team_name"] = team_name
                all_lineups.append(lineup_df)
        except Exception as e:
            print(f"  ERROR match_id={match_id} -- {e}")

    if not all_lineups:
        raise ValueError(
            "No lineup data was fetched — all lineup requests failed or returned nothing. "
            "Check the match IDs returned by extract_matches() and your StatsBomb credentials."
        )

    df = pd.concat(all_lineups, ignore_index=True)
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str)
    df = clean_column_names(df)
    df.to_parquet(f"{OUTPUT_DIR}/lineups/lineups.parquet", index=False)
    print(f"Saved {len(df)} lineup rows total")

if __name__ == "__main__":
    match_ids = extract_matches()
    extract_events(match_ids)
    extract_lineups(match_ids)
    print("Done. Parquet files saved to data/parquet/")
