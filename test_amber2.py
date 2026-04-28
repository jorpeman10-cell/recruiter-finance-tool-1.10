# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, 'advanced_analysis')
from okr_analyzer import OKRDataStore, OKRCalculator

store = OKRDataStore()
consultants = store.parse_and_save('D:/win设备桌面/2025年业绩核算/OKR 记录/OKR-2026.3.xlsx')

calc = OKRCalculator()

# Amber组织架构/人选变动
amber = [c for c in consultants if c.name == 'Amber'][0]
for i, r in enumerate(amber.rules):
    if '组织架构' in r.name:
        print('Rule', i, ':', r.name, ', base=', r.base_amount)
        for actual in [3, 3, 1, 4]:
            result = calc.calculate_rule_bonus(r, actual)
            print('  actual=', actual, '-> bonus=', result['bonus'])
