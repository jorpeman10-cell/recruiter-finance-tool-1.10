# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd

df = pd.read_excel('D:/win设备桌面/2025年业绩核算/OKR 记录/OKR-2026.3.xlsx', header=None)

# 检查所有有"开始计算"或"起算"的规则
for i in range(2, 70):
    rule = str(df.iloc[i, 11]) if pd.notna(df.iloc[i, 11]) else ''
    if '开始计算' in rule or '起算' in rule:
        project = df.iloc[i, 8] if pd.notna(df.iloc[i, 8]) else ''
        bonus = df.iloc[i, 13] if pd.notna(df.iloc[i, 13]) else 0
        print('Row', i, ':', project)
        print('  rule=', rule)
        print('  bonus=', bonus)
