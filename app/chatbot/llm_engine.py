# app/chatbot/llm_engine.py
import os
import json
import re
from groq import Groq
from google.cloud import bigquery
from .table_schema import TABLE_CONTEXT
from .marts_data_dict import MARTS_DATA_DICT

# Initialize Groq client using environment variable
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Initialize BigQuery client once at the module level
project_id = os.environ.get("GCP_PROJECT_ID", "football-capstone-mds-496219")
bq_client = bigquery.Client(project=project_id)

# Primary model: larger, more instruction-following
# Fallback: fast model if primary is unavailable
PRIMARY_MODEL  = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "llama-3.1-8b-instant"


def is_safe_sql(sql_query: str) -> bool:
    """Validates that the generated query is strictly a single, read-only SELECT statement."""
    clean_sql = sql_query.strip().upper()

    # Block multi-statement queries
    if ";" in clean_sql.rstrip(";"):
        return False

    # Block destructive DML/DDL or data modification keywords
    forbidden_keywords = [
        "DROP", "DELETE", "UPDATE", "INSERT", "MERGE", "CREATE",
        "ALTER", "GRANT", "CALL", "EXPORT", "TRUNCATE"
    ]
    for keyword in forbidden_keywords:
        if re.search(r'\b' + keyword + r'\b', clean_sql):
            return False

    # Block REPLACE only if it is not followed by an opening parenthesis
    if re.search(r'\bREPLACE\b(?!\s*\()', clean_sql):
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
        job_config = bigquery.QueryJobConfig(
            maximum_bytes_billed=200 * 1024 * 1024,  # 200MB limit
            use_query_cache=True
        )
        query_job = bq_client.query(sql, job_config=job_config)
        results = query_job.result()
        return [dict(row) for row in results]
    except Exception as e:
        print(f"[BigQuery Error]: {str(e)}")
        return [{"status": "Error", "message": "An error occurred while fetching the requested statistics."}]


def _chat(model: str, messages: list, tools: list = None, tool_choice: str = "auto"):
    """Wrapper that falls back to FALLBACK_MODEL if the primary model call fails."""
    kwargs = dict(messages=messages, temperature=0)
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice
    try:
        return client.chat.completions.create(model=model, **kwargs)
    except Exception as e:
        print(f"[Model fallback] {model} failed ({e}), retrying with {FALLBACK_MODEL}")
        return client.chat.completions.create(model=FALLBACK_MODEL, **kwargs)


def _format_fallback(query_data: list) -> str:
    """
    Safety net: if the LLM returns a response that doesn't contain any
    of the actual data values, format the rows directly so the user
    always sees the results.
    """
    if not query_data or (len(query_data) == 1 and "status" in query_data[0]):
        return None  # error row — let the LLM message stand

    lines = []
    for i, row in enumerate(query_data, 1):
        parts = [f"{k}: {v}" for k, v in row.items()]
        lines.append(f"{i}. {' | '.join(parts)}")
    return "\n".join(lines)


def _response_contains_data(answer: str, query_data: list) -> bool:
    """
    Check whether the LLM answer actually contains values from the
    query result (at least one player name or numeric value from row 1).
    """
    if not query_data or not answer:
        return True  # nothing to check
    first_row = query_data[0]
    for v in first_row.values():
        if str(v)[:6] in answer:  # first 6 chars of any value present → OK
            return True
    return False


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
                f"CRITICAL RULES:\n"
                f"1. ALWAYS call the 'query_bigquery' tool before answering any question about players, teams, or matches.\n"
                f"2. After receiving the tool result, you MUST present ALL the data rows as a formatted list or table. Never skip or omit any row.\n"
                f"3. Format each player/result on its own line with their stats clearly labeled (e.g., '1. Philip Foden — xG/90: 0.96').\n"
                f"4. Do NOT write introductory sentences without the data. Present the data immediately.\n"
                f"5. If the result is empty, say 'No results found' and explain why."
            )
        },
        {"role": "user", "content": user_query}
    ]

    try:
        response = _chat(PRIMARY_MODEL, messages, tools=tools)
    except Exception as e:
        return {
            "answer": f"Error: {str(e)}",
            "sql_query": None,
            "query_data": None,
        }

    assistant_message = response.choices[0].message
    tool_calls = assistant_message.tool_calls

    if tool_calls:
        sql_args = json.loads(tool_calls[0].function.arguments)
        sql_query = sql_args['sql']
        query_data = query_bigquery(sql_query)

        try:
            final_response = _chat(
                PRIMARY_MODEL,
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
            answer = final_response.choices[0].message.content

            # Fallback: if LLM answer doesn't actually contain the data, format it directly
            if not _response_contains_data(answer, query_data):
                fallback = _format_fallback(query_data)
                if fallback:
                    answer = fallback
        except Exception as e:
            answer = f"Error: {str(e)}"

        return {
            "answer": answer,
            "sql_query": sql_query,
            "query_data": query_data,
        }

    return {
        "answer": assistant_message.content,
        "sql_query": None,
        "query_data": None,
    }
