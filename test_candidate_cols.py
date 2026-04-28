import sys
sys.path.insert(0, 'advanced_analysis')
from gllue_db_client import GllueDBClient
import db_config_manager

client = GllueDBClient(db_config_manager.get_gllue_db_config())

# Check candidate columns for phone/email
print("=== candidate columns (phone/email related) ===")
r = client.query("SHOW COLUMNS FROM candidate")
for _, row in r.iterrows():
    col = str(row['Field']).lower()
    if 'phone' in col or 'mobile' in col or 'email' in col or 'tel' in col or 'contact' in col:
        print(f"  {row['Field']} ({row['Type']})")

# Show all columns
print("\n=== All candidate columns ===")
for _, row in r.iterrows():
    print(f"  {row['Field']}")

# Check sample candidate data
print("\n=== Sample candidates ===")
r2 = client.query("""
    SELECT id, englishName, chineseName, title, mobile, email, 
           CONCAT(IFNULL(englishName, ''), ' ', IFNULL(chineseName, '')) as full_name
    FROM candidate
    WHERE (englishName IS NOT NULL OR chineseName IS NOT NULL)
    LIMIT 5
""")
print(r2.to_string())

# Count total candidates
print("\n=== Candidate count ===")
r3 = client.query("SELECT COUNT(*) as cnt FROM candidate")
print(f"Total candidates: {r3.iloc[0]['cnt']}")
