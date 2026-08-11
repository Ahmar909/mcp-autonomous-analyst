import os
import sys
import duckdb
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from duckduckgo_search import DDGS
from dotenv import load_dotenv
from groq import Groq

# 1. Load hidden .env credentials
load_dotenv(dotenv_path="gemini.env")
GROQ_KEY = os.environ.get("GROQ_API_KEY")

if not GROQ_KEY:
    print("\n[CRITICAL ERROR]: GEMINI_API_KEY is missing from your .env file!")
    sys.exit(1)

# 2. App initialization
app = FastAPI(title="MCP Agentic Bridge")
ai_client = Groq(api_key=GROQ_KEY)

class UserPrompt(BaseModel):
    prompt: str

# ─── DEFINE DIRECT PYTHON TOOLS FOR GEMINI ─────────────────────────

def query_database(sql_query: str) -> str:
    """Executes a read-only SQL SELECT statement against the local company_metrics database table.
    
    Args:
        sql_query: The complete SQL string starting with SELECT.
    """
    print(f"\n[AGENT CALLS TOOL] Running SQL query: {sql_query}")
    
    if not sql_query.strip().lower().startswith("select"):
        return "Error: Only read-only SELECT queries are allowed."
        
    conn = duckdb.connect("analytics.db", read_only=True)
    try:
        result = conn.execute(sql_query).df().to_dict(orient="records")
        return str(result)
    except Exception as e:
        return f"Database Error: {str(e)}"
    finally:
        conn.close()


def live_web_search(query: str) -> str:
    """Searches the live web via DuckDuckGo for breaking news, current events, and external industry trends.
    
    Args:
        query: The specific search criteria or keywords.
    """
    print(f"\n[AGENT CALLS TOOL] Searching the web for: {query}")
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=3)
            if not results:
                return "No real-time web results found."
            
            summary = []
            for r in results:
                summary.append(f"Title: {r.get('title')}\nURL: {r.get('href')}\nSnippet: {r.get('body')}\n")
            return "\n".join(summary)
    except Exception as e:
        return f"Web Search Error: {str(e)}"

# ─── GROQ TOOL SCHEMAS ──────────────────────────────────────────────

tools = [
    {
        "type": "function",
        "function": {
            "name": "query_database",
            "description": "Executes a read-only SQL SELECT statement against the local company_metrics database table.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": "The complete SQL string starting with SELECT."
                    }
                },
                "required": ["sql_query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "live_web_search",
            "description": "Searches the live web via DuckDuckGo for breaking news, current events, and external industry trends.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The specific search criteria or keywords."
                    }
                },
                "required": ["query"]
            }
        }
    }
]
# Mapping tool names to executable functions
available_functions = {
    "query_database": query_database,
    "live_web_search": live_web_search
}

# ─── CORE CHAT ENDPOINT WITH AUTOMATIC ROUTING ─────────────────────

@app.post("/chat")
async def chat_endpoint(user_input: UserPrompt):
    try:
        print(f"\n[USER INPUT RECEIVED]: {user_input.prompt}")
        
        system_instruction = (
            "You are a professional Autonomous Data Analyst. You have access to a local database "
            "table named 'company_metrics' and a live web search tool. If the user asks about data "
            "you don't know, use query_database or live_web_search to find it out. Always double-check "
            "the table structure before reporting numbers."
        )
        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_input.prompt}
        ]
        # Initial call to Groq
        response = ai_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.2
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        # If model decides to call tools
        if tool_calls:
            messages.append(response_message)
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                function_to_call = available_functions[function_name]
                function_response = function_to_call(**function_args)
                
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response
                })
            
            # Second call to get final synthesized response
            second_response = ai_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages
            )
            final_text = second_response.choices[0].message.content
        else:
            final_text = response_message.content

        print(f"[AGENT RESPONDED SUCCESSFULLY]")
        return {"response": final_text}

    except Exception as e:
        print(f"[SERVER ERROR]: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))