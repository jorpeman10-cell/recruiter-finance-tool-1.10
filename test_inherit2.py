# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
df = pd.read_excel('D:/win设备桌面/2025年业绩核算/OKR 记录/OKR-2026.3.xlsx', header=None)

# 检查Amy的Row 53-56的列8
for i in range(53, 57):
    val = df.iloc[i, 8]
    print(f'Row {i}, col 8: type={type(val)}, repr={repr(val)}, str="{str(val)}"')
    print(f'  pd.notna={pd.notna(val)}')
    if pd.notna(val):
        print(f'  strip="{str(val).strip()}"')
