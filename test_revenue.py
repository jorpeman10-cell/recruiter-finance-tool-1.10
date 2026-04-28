import sys
sys.path.insert(0, 'advanced_analysis')
from gllue_db_client import GllueDBClient
import db_config_manager

client = GllueDBClient(db_config_manager.get_gllue_db_config())

# Check joborder revenue distribution
r = client.query('''
    SELECT 
        CONCAT(IFNULL(u.englishName, ''), ' ', IFNULL(u.chineseName, '')) as consultant,
        COUNT(*) as job_count,
        SUM(j.revenue) as total_revenue,
        AVG(j.revenue) as avg_revenue,
        SUM(CASE WHEN j.revenue IS NOT NULL AND j.revenue > 0 THEN 1 ELSE 0 END) as jobs_with_revenue
    FROM joborder j
    LEFT JOIN user u ON j.addedBy_id = u.id
    WHERE j.dateAdded >= DATE_SUB(NOW(), INTERVAL 180 DAY)
      AND j.is_deleted = 0
      AND u.status = 'Active'
    GROUP BY j.addedBy_id
    ORDER BY total_revenue DESC
''')
print('Joborder revenue stats (180 days):')
print(r.to_string())
print()

# Check forecast data for consultants
r2 = client.query('''
    SELECT 
        CONCAT(IFNULL(u.englishName, ''), ' ', IFNULL(u.chineseName, '')) as consultant,
        COUNT(*) as forecast_count,
        SUM(f.forecast_fee) as total_forecast_fee,
        SUM(fa.amount_after_tax) as total_assignment_amount
    FROM forecastassignment fa
    JOIN forecast f ON fa.forecast_id = f.id
    LEFT JOIN user u ON fa.user_id = u.id
    LEFT JOIN joborder jo ON f.job_order_id = jo.id
    WHERE f.close_date >= DATE_SUB(NOW(), INTERVAL 180 DAY)
      AND jo.jobStatus = 'Live'
      AND f.last_stage IS NOT NULL
      AND u.status = 'Active'
    GROUP BY fa.user_id
    ORDER BY total_forecast_fee DESC
''')
print('Forecast stats (180 days):')
print(r2.to_string())
