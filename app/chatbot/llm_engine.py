# app/chatbot/llm_engine.py
import os
import json
import re
from groq import Groq
from google.cloud import bigquery
from .table_schema import TABLE_CONTEXT

# Initialize Groq client using environment variable
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def is_safe_sql(sql_query: str) -> bool:
    """Validates that the generated query is strictly a single, read-only SELECT statement."""
    clean_sql = sql_query.strip().upper()
    
    # Block multi-statement queries
    if ";" in clean_sql.rstrip(";"):
        return False
        
    # Block destructive DML/DDL or data modification keywords
    forbidden_keywords = [
        "DROP", "DELETE", "UPDATE", "INSERT", "MERGE", "CREATE", 
        "ALTER", "GRANT", "CALL", "EXPORT", "TRUNCATE", "REPLACE"
    ]
    for keyword in forbidden_keywords:
        if re.search(r'\b' + keyword + r'\b', clean_sql):
            return False
            
    # Ensure it starts with safe read-only commands
    if not (clean_sql.startswith("SELECT") or clean_sql.startswith("WITH")):
        return False
        
    return True

def query_bigquery(sql):
    """Executes a validated read-only SQL command against BigQuery Mart datasets securely."""
    if not is_safe_sql(sql):
        print(f"[Security Block] Malicious or invalid SQL attempted: {sql}")
        return [{"status": "Error", "message": "Database query rejected: Unauthorized SQL statement structure."}]

    try:
        # Parameterize project ID to support multi-environment configurations
        project_id = os.environ.get("GCP_PROJECT_ID", "football-capstone-mds-496219")
        bq_client = bigquery.Client(project=project_id)
        
        # Guardrail: Limit maximum bytes billed (e.g., 50 MB) and enforce cache usage
        job_config = bigquery.QueryJobConfig(
            maximum_bytes_billed=50 * 1024 * 1024,  # 50MB Limit
            use_query_cache=True
        )
        
        query_job = bq_client.query(sql, job_config=job_config)
        results = query_job.result()
        
        return [dict(row) for row in results]
    except Exception as e:
        # Server-side logging for diagnostics
        print(f"[BigQuery Error]: {str(e)}")
        # Return generic error details to avoid fingerprinting and schema exposure
        return [{"status": "Error", "message": "An error occurred while fetching the requested statistics."}]

def ask_football_chatbot(user_query):
    """Main pipeline handling tool orchestration and response construction."""
    tools = [{
        "type": "function",
        "function": {
            "name": "query_bigquery",
            "description": "Query football analytics mart tables. Provides granular read-only metrics data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "Valid BigQuery Standard SQL SELECT statement query"}
                },
                "required": ["sql"]
            }
        }
    }]

    messages = [
        {
            "role": "system",
            "content": (
                f"You are an Elite European Football AI assistant. Use the 'query_bigquery' tool to fetch data. "
                f"Always generate valid BigQuery SQL using the strict rules and column schemas specified below:\n{TABLE_CONTEXT}\n"
                f"Important: Do not summarize or provide empty placeholders if data is present. Return precise configurations."
            )
        },
        {"role": "user", "content": user_query}
    ]

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0
    )

    assistant_message = response.choices[0].message
    tool_calls = assistant_message.tool_calls

    if tool_calls:
        sql_args = json.loads(tool_calls[0].function.arguments)
        sql_query = sql_args['sql']
        
        query_data = query_bigquery(sql_query)
        
        final_response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                messages[0],
                {"role": "user", "content": user_query},
                assistant_message,
                {
                    "role": "tool", 
                    "tool_call_id": tool_calls[0].id, 
                    "name": "query_bigquery", 
                    "content": json.dumps(query_data, default=str)
                }
            ]
        )
        return final_response.choices[0].message.content

    return assistant_message.content