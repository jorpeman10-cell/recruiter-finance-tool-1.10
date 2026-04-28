import sys
sys.path.insert(0, 'advanced_analysis')
from gllue_db_client import GllueDBClient
import db_config_manager

client = GllueDBClient(db_config_manager.get_gllue_db_config())

# Check candidate-related tables
print("=== Tables with candidate/resume ===")
for kw in ['candidate', 'resume', 'siteresume', 'hub_resume', 'me_resume']:
    try:
        r = client.query(f"SHOW TABLES LIKE '%{kw}%'")
        if not r.empty:
            print(f"\n{kw}:")
            for _, row in r.iterrows():
                print(f"  {row.iloc[0]}")
    except Exception as e:
        print(f"  {kw}: {e}")

# Check siteresume structure
print("\n=== siteresume columns (first 30) ===")
r = client.query("SHOW COLUMNS FROM siteresume")
for _, row in r.head(30).iterrows():
    print(f"  {row['Field']}")

# Check candidate structure
print("\n=== candidate columns (first 30) ===")
r2 = client.query("SHOW COLUMNS FROM candidate")
for _, row in r2.head(30).iterrows():
    print(f"  {row['Field']}")
