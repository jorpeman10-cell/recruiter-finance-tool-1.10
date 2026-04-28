# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd

df = pd.read_excel('D:/win设备桌面/2025年业绩核算/OKR 记录/OKR-2026.3.xlsx', header=None)

# Vivien奖金明细
print('Vivien奖金明细:')
for i in range(24, 28):
    project = df.iloc[i, 8] if pd.notna(df.iloc[i, 8]) else ''
    weight = df.iloc[i, 10] if pd.notna(df.iloc[i, 10]) else 0
    bonus = df.iloc[i, 13] if pd.notna(df.iloc[i, 13]) else 0
    print(' ', project, ': weight=', weight, ', bonus=', bonus)
