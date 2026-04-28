# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd

df = pd.read_excel('D:/win设备桌面/2025年业绩核算/OKR 记录/OKR-2026.3.xlsx', header=None)

# 检查Larry的Row 6-7
for i in range(6, 8):
    for col in [8, 9, 10, 11]:
        val = df.iloc[i, col]
        print('Row', i, ', col', col, ':', repr(val))
