import sys
sys.path.insert(0, 'advanced_analysis')
from gllue_db_client import GllueDBClient
import db_config_manager

client = GllueDBClient(db_config_manager.get_gllue_db_config())

# Check companyorganization structure
print("=== companyorganization columns ===")
r = client.query("SHOW COLUMNS FROM companyorganization")
for _, row in r.iterrows():
    print(f"  {row['Field']}")

print("\n=== Sample companyorganization data ===")
r2 = client.query("""
    SELECT id, name, client_id, addedBy_id, dateAdded, lastUpdateDate, status, 
           parent_id, level, department_id, post_id, member_id
    FROM companyorganization
    ORDER BY dateAdded DESC
    LIMIT 10
""")
print(r2.to_string())
print(f"\nTotal rows: {client.query('SELECT COUNT(*) as cnt FROM companyorganization').iloc[0]['cnt']}")

# Check if there's a diagram/image/blob field
print("\n=== Checking for blob/longtext fields ===")
r3 = client.query("""
    SELECT COLUMN_NAME, DATA_TYPE 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = 'companyorganization' 
      AND TABLE_SCHEMA = 'gllue'
      AND DATA_TYPE IN ('longtext', 'blob', 'mediumblob', 'longblob', 'json')
""")
print(r3.to_string())
