import sys
sys.path.insert(0, 'advanced_analysis')
from gllue_db_client import GllueDBClient
import db_config_manager

client = GllueDBClient(db_config_manager.get_gllue_db_config())

# Check cvsent columns
r = client.query("SHOW COLUMNS FROM cvsent")
print('CVsent columns:')
for _, row in r.iterrows():
    print(row['Field'])
print()

# Query cvsent counts by consultant for 2026
r2 = client.query('''
    SELECT 
        CONCAT(IFNULL(u.englishName, ''), ' ', IFNULL(u.chineseName, '')) as consultant,
        COUNT(*) as cnt
    FROM cvsent cs
    LEFT JOIN user u ON cs.user_id = u.id
    WHERE cs.dateAdded >= '2026-01-01'
      AND cs.active = 1
    GROUP BY cs.user_id
    ORDER BY cnt DESC
    LIMIT 15
''')
print('CVsent 2026 counts:')
print(r2.to_string())
print('Total:', r2['cnt'].sum())
print()

# Also check with signDate
r3 = client.query('''
    SELECT 
        CONCAT(IFNULL(u.englishName, ''), ' ', IFNULL(u.chineseName, '')) as consultant,
        COUNT(*) as cnt
    FROM cvsent cs
    LEFT JOIN user u ON cs.user_id = u.id
    WHERE cs.signDate >= '2026-01-01'
      AND cs.active = 1
    GROUP BY cs.user_id
    ORDER BY cnt DESC
    LIMIT 15
''')
print('CVsent 2026 signDate counts:')
print(r3.to_string())
print('Total:', r3['cnt'].sum())
