import duckdb
from fastmcp import FastMCP

# Initialize FastMCP - the standard high-level server wrapper
mcp = FastMCP("Autonomous Analyst Server")

def run_query(sql_query: str):
    """Helper function to safely query our local DuckDB database."""
    conn = duckdb.connect("analytics.db", read_only=True)
    try:
        # Fetch results as a list of dictionaries for clean JSON translation
        result = conn.execute(sql_query).df().to_dict(orient="records")
        return result
    except Exception as e:
        return f"Database Error: {str(e)}"
    finally:
        conn.close()

# Register a tool that the LLM can discover and use
@mcp.tool(name="query_database", description="Execute read-only SQL queries on the company_metrics table.")
def query_database(sql_query: str) -> str:
    # Basic guardrail ensuring the model doesn't try destructive actions
    if not sql_query.strip().lower().startswith("select"):
        return "Error: Only read-only SELECT queries are authorized."
        
    data = run_query(sql_query)
    return str(data)

# Register a passive resource displaying the database schema
@mcp.resource("analytics://database/schema")
def get_schema() -> str:
    """Returns the structure and columns of the company_metrics table."""
    conn = duckdb.connect("analytics.db", read_only=True)
    schema_info = conn.execute("DESCRIBE company_metrics;").fetchall()
    conn.close()
    
    schema_string = "Table: company_metrics\nColumns:\n"
    for col in schema_info:
        schema_string += f"- {col[0]} ({col[1]})\n"
    return schema_string