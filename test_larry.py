# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, 'advanced_analysis')
from okr_analyzer import OKRDataStore

store = OKRDataStore()
consultants = store.parse_and_save('D:/win设备桌面/2025年业绩核算/OKR 记录/OKR-2026.3.xlsx')

larry = [c for c in consultants if c.name == 'Larry'][0]
for i, r in enumerate(larry.rules):
    print('Rule', i, ':', r.name, ', target=', r.target_desc, ', base=', r.base_amount, ', period=', r.period)
