import sys
sys.path.insert(0, 'advanced_analysis')
from gllue_db_client import GllueDBClient
import db_config_manager

client = GllueDBClient(db_config_manager.get_gllue_db_config())

# Check offersign consultant names
r1 = client.query('''
    SELECT DISTINCT
        CONCAT(IFNULL(u.englishName, ''), ' ', IFNULL(u.chineseName, '')) as consultant
    FROM offersign os
    LEFT JOIN user u ON os.user_id = u.id
    WHERE os.signDate >= '2026-01-01'
      AND os.active = 1
''')
print('Offersign consultants:')
for c in r1['consultant'].dropna():
    print(f"  [{c}]")
print()

# Check cvsent consultant names  
r2 = client.query('''
    SELECT DISTINCT
        CONCAT(IFNULL(u.englishName, ''), ' ', IFNULL(u.chineseName, '')) as consultant
    FROM cvsent cs
    LEFT JOIN user u ON cs.user_id = u.id
    WHERE cs.dateAdded >= '2026-01-01'
      AND cs.active = 1
''')
print('CVsent consultants (top 15):')
for c in r2['consultant'].dropna().head(15):
    print(f"  [{c}]")
print()

# Direct count for Daisy
r3 = client.query('''
    SELECT COUNT(*) as cnt
    FROM offersign os
    LEFT JOIN user u ON os.user_id = u.id
    WHERE os.signDate >= '2026-01-01'
      AND os.active = 1
      AND u.englishName = 'Daisy'
''')
print('Daisy offers:', r3.iloc[0]['cnt'])
