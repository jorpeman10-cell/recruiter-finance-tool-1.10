import sys
sys.path.insert(0, 'advanced_analysis')
from gllue_db_client import GllueDBClient
import db_config_manager

client = GllueDBClient(db_config_manager.get_gllue_db_config())

# Check cache content
print("=== companyorganizationcache sample ===")
r = client.query("""
    SELECT id, uuid, LENGTH(content) as content_len, content
    FROM companyorganizationcache
    WHERE content IS NOT NULL AND content != ''
    LIMIT 5
""")
if not r.empty:
    for _, row in r.iterrows():
        print(f"ID: {row['id']}, UUID: {row['uuid']}, Content length: {row['content_len']}")
        content = str(row['content'])[:500]
        print(f"Content preview: {content}")
        print("---")
else:
    print("No content found")

# Check total cache count
print("\n=== Cache count ===")
r2 = client.query("SELECT COUNT(*) as cnt FROM companyorganizationcache")
print(f"Total cache rows: {r2.iloc[0]['cnt']}")

# Check mapping between companyorganization and cache
print("\n=== Check if companyorganization has uuid field ===")
r3 = client.query("SHOW COLUMNS FROM companyorganization")
uuid_col = None
for _, row in r3.iterrows():
    if 'uuid' in str(row['Field']).lower() or 'cache' in str(row['Field']).lower():
        uuid_col = row['Field']
        print(f"Found: {row['Field']}")

# Check version field meaning
print("\n=== version distribution ===")
r4 = client.query("SELECT version, COUNT(*) as cnt FROM companyorganization GROUP BY version")
print(r4.to_string())
