# llm_engine.py
import json
import os
import sys
from pathlib import Path

from groq import Groq
from google.cloud import bigquery

from .table_schema import TABLE_CONTEXT

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.chatbot.prompts import FOOTBALL_SYSTEM_PROMPT

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
# bq_client = bigquery.Client()


def query_bigquery(sql):
    """Mocks BigQuery results based on the generated SQL for demo purposes."""
    sql_lower = sql.lower()

    if "mart_player_clusters" in sql_lower:
        return [
            {"player_name": "Rodri", "cluster_label": "Deep-Lying Playmaker"},
            {"player_name": "Declan Rice", "cluster_label": "Ball-Winning Midfielder"},
            {"player_name": "Joshua Kimmich", "cluster_label": "Deep-Lying Playmaker"},
        ]

    if "mart_match_prediction_features" in sql_lower:
        return [
            {"feature": "home_rolling_xg_5", "description": "Home team rolling 5-match xG"},
            {"feature": "away_rolling_xg_5", "description": "Away team rolling 5-match xG"},
            {"feature": "home_rolling_points_5", "description": "Home team rolling 5-match form"},
            {"feature": "home_adv", "description": "Home advantage indicator"},
        ]

    if "mart_player_performance" in sql_lower and (
        "international" in sql_lower or "club" in sql_lower or "is_international" in sql_lower
    ):
        return [
            {
                "context": "club",
                "avg_xg_per_90": 0.42,
            },
            {
                "context": "international",
                "avg_xg_per_90": 0.31,
            },
            {"avg_shift_club_minus_international": 0.11},
        ]

    if "mart_player_performance" in sql_lower:
        return [
            {"player_name": "Erling Haaland", "goals_per_90": 1.1, "xg_per_90": 0.95},
            {"player_name": "Kylian Mbappé", "goals_per_90": 0.85, "xg_per_90": 0.82},
        ]

    if "pressure" in sql_lower or "liga" in sql_lower or "premier" in sql_lower:
        return [
            {"competition": "Premier League", "avg_pressures_per_90": 42.55},
            {"competition": "La Liga", "avg_pressures_per_90": 40.91},
        ]

    return [
        {
            "status": "Success",
            "message": "Query executed, but no specific mock data found for this table.",
        }
    ]


def ask_football_chatbot(user_query):
    tools = [
        {
            "type": "function",
            "function": {
                "name": "query_bigquery",
                "description": "Query football analytics mart tables. " + TABLE_CONTEXT,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "The BigQuery SQL query"}
                    },
                    "required": ["sql"],
                },
            },
        }
    ]

    messages = [
        {"role": "system", "content": FOOTBALL_SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0,
    )

    tool_calls = response.choices[0].message.tool_calls
    if tool_calls:
        sql = json.loads(tool_calls[0].function.arguments)["sql"]
        data = query_bigquery(sql)

        final_response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": FOOTBALL_SYSTEM_PROMPT},
                {"role": "user", "content": user_query},
                {"role": "assistant", "content": None, "tool_calls": tool_calls},
                {"role": "tool", "tool_call_id": tool_calls[0].id, "content": str(data)},
            ],
        )
        return final_response.choices[0].message.content

    return response.choices[0].message.content
