from sqlalchemy import create_engine, inspect

# Use your connection URL
DATABASE_URL = "postgresql://postgres:Robbo2004!@127.0.0.1:5432/case_advocates"
engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

print("--- DATABASE SCHEMA INSPECTION ---")

# Look at your target tables
target_tables = ["users", "consultation_requests"]

for table in target_tables:
    if table in inspector.get_table_names():
        print(f"\n📋 Table Name: '{table}'")
        print("Columns found:")
        for column in inspector.get_columns(table):
            # Prints column name and its variable type (e.g., VARCHAR, INT)
            print(f"  🔹 {column['name']} ({column['type']})")
    else:
        print(f"\n❌ Table '{table}' was not found in the database!")

print("\n---------------------------------")
