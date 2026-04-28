import sys
sys.path.insert(0, 'advanced_analysis')
from gllue_db_client import GllueDBClient
import db_config_manager

client = GllueDBClient(db_config_manager.get_gllue_db_config())

# Correct sample query
print("=== Sample companyorganization ===")
r = client.query("""
    SELECT id, name, client_id, client_name, addedBy_id, joborder_id, 
           dateAdded, version, is_deleted
    FROM companyorganization
    ORDER BY dateAdded DESC
    LIMIT 10
""")
print(r.to_string())

# Count by client
print("\n=== Top clients by org chart count ===")
r2 = client.query("""
    SELECT client_name, COUNT(*) as cnt
    FROM companyorganization
    WHERE is_deleted = 0
    GROUP BY client_id
    ORDER BY cnt DESC
    LIMIT 15
""")
print(r2.to_string())

# Check if there are related tables with diagram data
print("\n=== Tables related to companyorganization ===")
r3 = client.query("SHOW TABLES LIKE '%companyorganization%'")
for _, row in r3.iterrows():
    print(f"  {row.iloc[0]}")

# Check companyorganizationcache
print("\n=== companyorganizationcache columns ===")
r4 = client.query("SHOW COLUMNS FROM companyorganizationcache")
for _, row in r4.iterrows():
    print(f"  {row['Field']}")

print("\n=== Sample cache ===")
r5 = client.query("""
    SELECT * FROM companyorganizationcache
    LIMIT 3
""")
print(r5.to_string())
