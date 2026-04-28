import sys
sys.path.insert(0, 'advanced_analysis')
from gllue_db_client import GllueDBClient
import db_config_manager
from consultant_performance import ConsultantPerformanceAnalyzer

client = GllueDBClient(db_config_manager.get_gllue_db_config())
perf = ConsultantPerformanceAnalyzer(client)
perf.load_from_db('2026-01-01')

print('cvsents shape:', perf._cvsents.shape if perf._cvsents is not None else None)
print('interviews shape:', perf._interviews.shape if perf._interviews is not None else None)
print('offers shape:', perf._offers.shape if perf._offers is not None else None)
print('onboards shape:', perf._onboards.shape if perf._onboards is not None else None)
print()

if perf._offers is not None and not perf._offers.empty:
    print('Offer consultants:')
    for c in perf._offers['consultant'].dropna().unique():
        print(f"  [{c}]")
    print()
    
    print('Offer counts by consultant:')
    print(perf._offers.groupby('consultant').size().to_string())
    print()

if perf._cvsents is not None and not perf._cvsents.empty:
    print('CV consultant sample:')
    for c in perf._cvsents['consultant'].dropna().unique()[:5]:
        print(f"  [{c}]")
    print()

# Check name match for Daisy
if perf._offers is not None and perf._cvsents is not None:
    daisy_cv = perf._cvsents[perf._cvsents['consultant'].str.contains('Daisy', na=False)]
    daisy_offer = perf._offers[perf._offers['consultant'].str.contains('Daisy', na=False)]
    print(f'Daisy cvsents: {len(daisy_cv)}')
    print(f'Daisy offers: {len(daisy_offer)}')
