import sys
sys.path.insert(0, 'advanced_analysis')
from gllue_db_client import GllueDBClient
import db_config_manager

client = GllueDBClient(db_config_manager.get_gllue_db_config())

# Check offersign revenue (actual historical revenue)
r = client.query('''
    SELECT 
        CONCAT(IFNULL(u.englishName, ''), ' ', IFNULL(u.chineseName, '')) as consultant,
        COUNT(*) as offer_count,
        SUM(os.revenue) as total_revenue,
        AVG(os.revenue) as avg_revenue
    FROM offersign os
    LEFT JOIN user u ON os.user_id = u.id
    WHERE os.signDate >= DATE_SUB(NOW(), INTERVAL 365 DAY)
      AND os.active = 1
      AND u.status = 'Active'
    GROUP BY os.user_id
    ORDER BY total_revenue DESC
''')
print('Offersign revenue stats (365 days):')
print(r.to_string())
print()

# Check joborder for fee-related fields
r2 = client.query('''
    SELECT 
        annualSalary, revenue, percentage, monthSalary, maxMonthlySalary,
        maxAnnualSalary, estimatedOnboardDate
    FROM joborder
    WHERE revenue IS NOT NULL AND revenue > 0
    LIMIT 5
''')
print('Joborder with revenue:')
print(r2.to_string())
print()

# Check if there's estimated_fee or similar
r3 = client.query('''
    SELECT 
        annualSalary, revenue, percentage, monthSalary, is_minimal_fee
    FROM joborder
    WHERE is_minimal_fee = 1
    LIMIT 3
''')
print('Joborder minimal fee:')
print(r3.to_string())
