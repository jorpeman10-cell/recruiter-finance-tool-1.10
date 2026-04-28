import sys
sys.path.insert(0, 'advanced_analysis')
from gllue_db_client import GllueDBClient
import db_config_manager

client = GllueDBClient(db_config_manager.get_gllue_db_config())

# Check clientinterview counts by consultant for 2026
r = client.query('''
    SELECT 
        CONCAT(IFNULL(u.englishName, ''), ' ', IFNULL(u.chineseName, '')) as consultant,
        COUNT(*) as cnt
    FROM clientinterview ci
    JOIN jobsubmission js ON ci.jobsubmission_id = js.id
    LEFT JOIN user u ON js.user_id = u.id
    WHERE ci.date >= '2026-01-01'
      AND ci.active = 1
    GROUP BY js.user_id
    ORDER BY cnt DESC
    LIMIT 15
''')
print('Clientinterview 2026 counts:')
print(r.to_string())
print('Total:', r['cnt'].sum())
print()

# Check offersign counts
r2 = client.query('''
    SELECT 
        CONCAT(IFNULL(u.englishName, ''), ' ', IFNULL(u.chineseName, '')) as consultant,
        COUNT(*) as cnt
    FROM offersign os
    LEFT JOIN user u ON os.user_id = u.id
    WHERE os.signDate >= '2026-01-01'
      AND os.active = 1
    GROUP BY os.user_id
    ORDER BY cnt DESC
    LIMIT 15
''')
print('Offersign 2026 counts:')
print(r2.to_string())
print('Total:', r2['cnt'].sum())
