import sys
sys.path.insert(0, 'advanced_analysis')
from gllue_db_client import GllueDBClient
import db_config_manager
from consultant_performance import ConsultantPerformanceAnalyzer

client = GllueDBClient(db_config_manager.get_gllue_db_config())
perf = ConsultantPerformanceAnalyzer(client)
perf.load_from_db('2026-01-01')

funnel = perf.get_funnel_analysis()
print('=== Funnel Analysis (2026 YTD) ===')
print(funnel[['顾问', '推荐数', '面试数', 'Offer数', '入职数', '推荐到面试率', '面试到Offer率', '推荐到Offer率']].head(12).to_string())
print()
print('Totals:')
print(f"  推荐: {funnel['推荐数'].sum()}")
print(f"  面试: {funnel['面试数'].sum()}")
print(f"  Offer: {funnel['Offer数'].sum()}")
print(f"  入职: {funnel['入职数'].sum()}")
