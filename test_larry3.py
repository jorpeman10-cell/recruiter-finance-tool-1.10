# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, 'advanced_analysis')
from okr_analyzer import OKRDataStore

store = OKRDataStore()
consultants = store.parse_and_save('D:/win设备桌面/2025年业绩核算/OKR 记录/OKR-2026.3.xlsx')

# Larry的period是什么？
larry = [c for c in consultants if c.name == 'Larry'][0]
for i, r in enumerate(larry.rules):
    print('Rule', i, ':', r.name, ', period=', r.period, ', threshold_full=', r.threshold_full_bonus)
    is_ratio = (r.period == 'quarterly' and 1.533 != int(1.533) and r.threshold_full_bonus == 0)
    print('  actual=1.533, is_ratio=', is_ratio)
