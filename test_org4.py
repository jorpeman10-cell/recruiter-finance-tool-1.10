import sys
sys.path.insert(0, 'advanced_analysis')
from gllue_db_client import GllueDBClient
import db_config_manager

client = GllueDBClient(db_config_manager.get_gllue_db_config())

# Check all columns of companyorganization carefully
print("=== All companyorganization columns with types ===")
r = client.query("""
    SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'companyorganization'
      AND TABLE_SCHEMA = 'gllue'
    ORDER BY ORDINAL_POSITION
""")
print(r.to_string())

# Check companyorganizationmapping
print("\n=== companyorganizationmapping columns ===")
r2 = client.query("SHOW COLUMNS FROM companyorganizationmapping")
for _, row in r2.iterrows():
    print(f"  {row['Field']}")

print("\n=== Sample mapping ===")
r3 = client.query("SELECT * FROM companyorganizationmapping LIMIT 5")
print(r3.to_string())

# Check if there's a separate diagram/image storage
print("\n=== Searching for content/diagram tables ===")
for kw in ['content', 'diagram', 'image', 'json', 'data', 'blob']:
    try:
        result = client.query(f"SHOW TABLES LIKE '%{kw}%'")
        if not result.empty:
            print(f"\nTables with '{kw}':")
            for _, row in result.iterrows():
                print(f"  {row.iloc[0]}")
    except:
        pass
