import sys
sys.path.insert(0, 'advanced_analysis')
from gllue_db_client import GllueDBClient
import db_config_manager

client = GllueDBClient(db_config_manager.get_gllue_db_config())

# Check tables related to cv/sent
r = client.query("SHOW TABLES LIKE '%cvsent%'")
print('CV sent tables:')
print(r.to_string())
print()

# Check all tables with 'sent' in name
r2 = client.query("SHOW TABLES LIKE '%sent%'")
print('Sent tables:')
print(r2.to_string())
print()

# Also check jobsubmission columns to understand the data better
r3 = client.query("SHOW COLUMNS FROM jobsubmission")
print('Jobsubmission columns (first 30):')
for _, row in r3.head(30).iterrows():
    print(row['Field'])
