# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, 'advanced_analysis')
from okr_analyzer import OKRDataStore, OKRCalculator

store = OKRDataStore()
consultants = store.parse_and_save('D:/win设备桌面/2025年业绩核算/OKR 记录/OKR-2026.3.xlsx')

calc = OKRCalculator()

# Vimber F2F
vimber = [c for c in consultants if c.name == 'Vimber'][0]
for i, r in enumerate(vimber.rules):
    if 'F2F' in r.name:
        print('Rule', i, ':', r.name, ', base=', r.base_amount)
        result = calc.calculate_rule_bonus(r, 3)
        print('  actual=3 -> bonus=', result['bonus'])

# Amber 组织架构
amber = [c for c in consultants if c.name == 'Amber'][0]
for i, r in enumerate(amber.rules):
    if '组织架构' in r.name:
        print('Rule', i, ':', r.name, ', base=', r.base_amount)
        for actual in [3, 3, 1, 4]:
            result = calc.calculate_rule_bonus(r, actual)
            print('  actual=', actual, '-> bonus=', result['bonus'])
