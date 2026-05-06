import os
import pandas as pd
from statsbombpy import sb
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = "data/parquet"
os.makedirs(f"{OUTPUT_DIR}/matches", exist_ok=True)
os.makedirs(f"{OUTPUT_DIR}/events", exist_ok=True)
os.makedirs(f"{OUTPUT_DIR}/lineups", exist_ok=True)

# La Liga = competition_id 11, season 2020/2021 = season_id 90
COMPETITION_ID = 11
SEASON_ID = 90

def clean_column_names(df):
    import re
    df.columns = [
        re.sub(r'[.\s]', '_', col)  # replace dots and spaces with underscore
           .replace('-', '_')        # replace hyphens
           for col in df.columns
    ]
    # prefix columns starting with a number
    df.columns = [f"col_{col}" if col[0].isdigit() else col for col in df.columns]
    return df

def extract_matches():
    print("Extracting matches...")
    matches = sb.matches(competition_id=COMPETITION_ID, season_id=SEASON_ID)
    matches = pd.json_normalize(matches.to_dict(orient="records"))
    matches.to_parquet(f"{OUTPUT_DIR}/matches/matches.parquet", index=False)
    print(f"Saved {len(matches)} matches")
    return matches["match_id"].tolist()

def extract_events(match_ids):
    print("Extracting events...")
    all_events = []
    for i, match_id in enumerate(match_ids):
        print(f"  Events {i+1}/{len(match_ids)} match_id={match_id}")
        events = sb.events(match_id=match_id)
        events["match_id"] = match_id
        all_events.append(events)
    df = pd.concat(all_events, ignore_index=True)
    # flatten any remaining dict columns
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
    print(f"Saved {len(df)} events")

def extract_lineups(match_ids):
    print("Extracting lineups...")
    all_lineups = []
    for i, match_id in enumerate(match_ids):
        print(f"  Lineups {i+1}/{len(match_ids)} match_id={match_id}")
        lineups = sb.lineups(match_id=match_id)
        for team_name, lineup_df in lineups.items():
            lineup_df["match_id"] = match_id
            lineup_df["team_name"] = team_name
            all_lineups.append(lineup_df)
    df = pd.concat(all_lineups, ignore_index=True)
    df.to_parquet(f"{OUTPUT_DIR}/lineups/lineups.parquet", index=False)
    print(f"Saved {len(df)} lineup rows")

if __name__ == "__main__":
    match_ids = extract_matches()
    extract_events(match_ids)
    extract_lineups(match_ids)
    print("Done. Parquet files saved to data/parquet/")
