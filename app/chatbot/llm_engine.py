# llm_engine.py
import os
from groq import Groq
from google.cloud import bigquery
from .table_schema import TABLE_CONTEXT

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
# bq_client = bigquery.Client()

def query_bigquery(sql):
    """Mocks BigQuery results based on the generated SQL for demo purposes."""
    sql_lower = sql.lower()
    
    # Mock Response 1: Player Archetypes/Clusters
    if "mart_player_clusters" in sql_lower:
        return [
            {"player_name": "Rodri", "cluster": "Deep-Lying Playmaker", "similarity": 0.98},
            {"player_name": "Declan Rice", "cluster": "Ball-Winning Midfielder", "similarity": 0.85},
            {"player_name": "Joshua Kimmich", "cluster": "Deep-Lying Playmaker", "similarity": 0.92}
        ]
    
    # Mock Response 2: Performance Metrics
    elif "mart_player_performance" in sql_lower:
        return [
            {"player_name": "Erling Haaland", "goals_per_90": 1.1, "xg_per_90": 0.95},
            {"player_name": "Kylian Mbappé", "goals_per_90": 0.85, "xg_per_90": 0.82}
        ]
    
    # Default Fallback
    return [{"status": "Success", "message": "Query executed, but no specific mock data found for this table."}]

def ask_football_chatbot(user_query):
    # Define the tool for the LLM
    tools = [{
        "type": "function",
        "function": {
            "name": "query_bigquery",
            "description": "Query football analytics mart tables. " + TABLE_CONTEXT,
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "The BigQuery SQL query"}
                },
                "required": ["sql"]
            }
        }
    }]

    messages = [
        {
            "role": "system",
            "content": (
                "You are an Elite European Football AI assistant. "
                "Use the 'query_bigquery' tool to fetch data for player performance, "
                "tactical clusters, or match statistics. "
                "Always generate valid BigQuery SQL based on the provided table schemas. "
                "Do not explain your reasoning before calling the tool."
            )
        },
        {"role": "user", "content": user_query}
    ]

    # 1. Ask LLM to generate SQL
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",  # Use Llama 3.1
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0  # Ensures consistent tool selection
    )

    # 2. Check if the LLM wants to call the tool
    tool_calls = response.choices[0].message.tool_calls
    if tool_calls:
        import json
        sql = json.loads(tool_calls[0].function.arguments)['sql']
        
        # 3. Get real data from BigQuery
        data = query_bigquery(sql)
        
        # 4. Return data to LLM for final natural language summary
        final_response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "user", "content": user_query},
                {"role": "assistant", "content": None, "tool_calls": tool_calls},
                {"role": "tool", "tool_call_id": tool_calls[0].id, "content": str(data)}
            ]
        )
        return final_response.choices[0].message.content

    return response.choices[0].message.content