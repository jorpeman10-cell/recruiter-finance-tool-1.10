import sys
sys.path.insert(0, 'advanced_analysis')
from gllue_db_client import GllueDBClient
import db_config_manager

client = GllueDBClient(db_config_manager.get_gllue_db_config())

query = """
    SELECT 
        os.id as offer_id,
        os.jobsubmission_id,
        os.user_id,
        CONCAT(IFNULL(u.englishName, ''), ' ', IFNULL(u.chineseName, '')) as consultant,
        os.signDate as sign_date,
        os.revenue as fee_amount,
        os.annualSalary,
        jo.jobTitle as position_name,
        c.name as client_name
    FROM offersign os
    LEFT JOIN user u ON os.user_id = u.id
    LEFT JOIN joborder jo ON os.job_order_id = jo.id
    LEFT JOIN client c ON jo.client_id = c.id
    WHERE os.signDate >= '2026-01-01'
      AND os.signDate <= '2026-04-30'
      AND os.active = 1
"""

result = client.query(query)
print('Result type:', type(result))
print('Result shape:', result.shape if hasattr(result, 'shape') else 'N/A')
if result is not None and hasattr(result, 'to_string'):
    print(result.to_string())
