# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
sys.path.insert(0, 'advanced_analysis')
from okr_analyzer import OKRDataStore

store = OKRDataStore()
consultants = store.parse_and_save('D:/win设备桌面/2025年业绩核算/OKR 记录/OKR-2026.3.xlsx')

# Amber的组织架构/人选变动
# Excel: Row 42 actual=3, bonus=50; Row 43 actual=3, bonus=50; Row 44 actual=1, bonus=0; Row 45 actual=4, bonus=50
# 看起来每周基础奖金是50元，不是25元
# 规则文本: 收集3个开始计算，3个25元一周;5个50元一周
# 但Excel中所有bonus都是50或0，没有25
# 可能是实际执行时统一为50元

amber = [c for c in consultants if c.name == 'Amber'][0]
for i, r in enumerate(amber.rules):
    if '组织架构' in r.name:
        print(f'Rule {i}: {r.name}, base={r.base_amount}, tier={r.tier_rules}')
