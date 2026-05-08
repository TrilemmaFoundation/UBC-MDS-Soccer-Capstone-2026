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

# competitions to include (matching your chart)
TARGET_COMPETITIONS = [
    "La Liga",
    "Ligue 1",
    "Premier League",
    "Serie A",
    "1. Bundesliga",
    "Indian Super League",
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
    print(f"Extracting events for {len(match_ids)} matches...")
    all_events = []
    for i, match_id in enumerate(match_ids):
        print(f"  Events {i+1}/{len(match_ids)} match_id={match_id}")
        try:
            events = sb.events(match_id=match_id)
            events["match_id"] = match_id
            all_events.append(events)
        except Exception as e:
            print(f"  ERROR match_id={match_id} -- {e}")

    df = pd.concat(all_events, ignore_index=True)
    for col in df.columns:
        if df[col].dtype == object:
            try:
                sample = df[col].dropna().iloc[0]
                if isinstance(sample, dict):
                    normalized = pd.json_normalize(df[col].apply(lambda x: x if isinstance(x, dict) else {}))
                    normalized.columns = [f"{col}.{c}" for c in normalized.columns]
                    df = pd.concat([df.drop(columns=[col]), normalized], axis=1)
            except (IndexError, Exception):
                pass
    df = clean_column_names(df)
    df.to_parquet(f"{OUTPUT_DIR}/events/events.parquet", index=False)
    print(f"Saved {len(df)} events total")

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

    df = pd.concat(all_lineups, ignore_index=True)
    df = clean_column_names(df)
    df.to_parquet(f"{OUTPUT_DIR}/lineups/lineups.parquet", index=False)
    print(f"Saved {len(df)} lineup rows total")

if __name__ == "__main__":
    match_ids = extract_matches()
    extract_events(match_ids)
    extract_lineups(match_ids)
    print("Done. Parquet files saved to data/parquet/")
