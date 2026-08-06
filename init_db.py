import duckdb

def initialize_database():
    print("Connecting to (or creating) analytics.db...")
    # This creates a persistent database file in your folder
    conn = duckdb.connect("analytics.db")
    
    print("Loading data.csv into a DuckDB table...")
    # DuckDB can directly read and convert a CSV implicitly
    conn.execute("CREATE OR REPLACE TABLE company_metrics AS SELECT * FROM read_csv_auto('data.csv');")
    
    # Let's verify it worked by checking the table layout
    print("\nSuccessfully initialized! Table structure:")
    print(conn.execute("DESCRIBE company_metrics;").fetchall())
    conn.close()

if __name__ == "__main__":
    initialize_database()