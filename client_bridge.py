import os
import sys
import duckdb
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
from google.genai import types
from duckduckgo_search import DDGS
from dotenv import load_dotenv

# 1. Load hidden .env credentials
load_dotenv(dotenv_path="gemini.env")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_KEY:
    print("\n[CRITICAL ERROR]: GEMINI_API_KEY is missing from your .env file!")
    sys.exit(1)

# 2. App initialization
app = FastAPI(title="MCP Agentic Bridge")
ai_client = genai.Client(api_key=GEMINI_KEY)

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

# ─── CORE CHAT ENDPOINT WITH AUTOMATIC ROUTING ─────────────────────

@app.post("/chat")
async def chat_endpoint(user_input: UserPrompt):
    try:
        print(f"\n[USER INPUT RECEIVED]: {user_input.prompt}")
        
        # We pass the python functions directly inside the tools array. 
        # Gemini implicitly inspects their docstrings and executes them natively.
        config = types.GenerateContentConfig(
            system_instruction=(
                "You are a professional Autonomous Data Analyst. You have access to a local database "
                "table named 'company_metrics' and a live web search tool. If the user asks about data "
                "you don't know, use query_database or live_web_search to find it out. Always double-check "
                "the table structure before reporting numbers."
            ),
            tools=[query_database, live_web_search],
            temperature=0.2
        )

        # Execute using automatic function routing loops
        response = ai_client.models.generate_content(
            model='gemini-3.5-flash',
            contents=user_input.prompt,
            config=config
        )

        print(f"[AGENT RESPONDED SUCCESSFULLY]")
        return {"response": response.text}

    except Exception as e:
        print(f"[SERVER ERROR]: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))