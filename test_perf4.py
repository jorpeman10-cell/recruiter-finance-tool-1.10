import sys
sys.path.insert(0, 'advanced_analysis')
from gllue_db_client import GllueDBClient
import db_config_manager

client = GllueDBClient(db_config_manager.get_gllue_db_config())

# Check offersign columns
r = client.query("SHOW COLUMNS FROM offersign")
print('Offersign columns:')
for _, row in r.iterrows():
    print(row['Field'])
print()

# Test simple query without joins
r2 = client.query("""
    SELECT id, jobsubmission_id, user_id, signDate, revenue
    FROM offersign
    WHERE signDate >= '2026-01-01'
      AND active = 1
    LIMIT 5
""")
print('Simple query:')
print(r2.to_string())
print()

# Test with user join only
r3 = client.query("""
    SELECT os.id, os.jobsubmission_id, os.user_id, os.signDate,
           CONCAT(IFNULL(u.englishName, ''), ' ', IFNULL(u.chineseName, '')) as consultant
    FROM offersign os
    LEFT JOIN user u ON os.user_id = u.id
    WHERE os.signDate >= '2026-01-01'
      AND os.active = 1
    LIMIT 5
""")
print('With user join:')
print(r3.to_string())
