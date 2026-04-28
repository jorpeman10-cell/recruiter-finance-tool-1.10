import sys
sys.path.insert(0, 'advanced_analysis')
from gllue_db_client import GllueDBClient
import db_config_manager

client = GllueDBClient(db_config_manager.get_gllue_db_config())

# Search for mapping/mindmap/org chart related tables
keywords = ['map', 'mind', 'org', 'chart', 'structure', 'tree', 'node', 'diagram', 'graph']

print("=== Searching for mapping-related tables ===")
for kw in keywords:
    try:
        r = client.query(f"SHOW TABLES LIKE '%{kw}%'")
        if not r.empty:
            print(f"\nKeyword '{kw}':")
            for _, row in r.iterrows():
                print(f"  {row.iloc[0]}")
    except Exception as e:
        print(f"  {kw}: error - {e}")

# Also check for tables with 'mapping' in various forms
print("\n=== Tables with 'mapping' ===")
try:
    r = client.query("SHOW TABLES LIKE '%mapping%'")
    if not r.empty:
        for _, row in r.iterrows():
            print(f"  {row.iloc[0]}")
    else:
        print("  No mapping tables found")
except Exception as e:
    print(f"  error: {e}")

# Check for orgchart or company structure
print("\n=== Tables with 'org%' ===")
try:
    r = client.query("SHOW TABLES LIKE 'org%'")
    if not r.empty:
        for _, row in r.iterrows():
            print(f"  {row.iloc[0]}")
    else:
        print("  No org tables found")
except Exception as e:
    print(f"  error: {e}")
