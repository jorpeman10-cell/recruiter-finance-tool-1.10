# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd

df = pd.read_excel('D:/win设备桌面/2025年业绩核算/OKR 记录/OKR-2026.3.xlsx', header=None)

# 分析有"开始计算"的规则
print('BD list bonuses:')
for i in range(37, 41):
    bonus = df.iloc[i, 13] if pd.notna(df.iloc[i, 13]) else 0
    print('  Row', i, ': bonus=', bonus)

print('组织架构/人选变动 bonuses:')
for i in range(42, 46):
    bonus = df.iloc[i, 13] if pd.notna(df.iloc[i, 13]) else 0
    print('  Row', i, ': bonus=', bonus)

print('F2F bonuses:')
for i in range(63, 67):
    bonus = df.iloc[i, 13] if pd.notna(df.iloc[i, 13]) else 0
    print('  Row', i, ': bonus=', bonus)
