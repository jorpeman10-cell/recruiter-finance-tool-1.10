# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
sys.path.insert(0, 'advanced_analysis')
from okr_analyzer import OKRParser

df = pd.read_excel('D:/win设备桌面/2025年业绩核算/OKR 记录/OKR-2026.3.xlsx', header=None)

# 检查Amy的start=47, main_project是什么
start = 47
main_project = str(df.iloc[start, 8]).strip() if pd.notna(df.iloc[start, 8]) else ''
print(f'main_project from Row {start}: {main_project}')

# 检查Row 53-56
for row in [53, 54, 55, 56]:
    project = str(df.iloc[row, 8]).strip() if pd.notna(df.iloc[row, 8]) else ''
    print(f'Row {row} project: "{project}"')
    print(f'  not project: {not project}')
    print(f'  row > start: {row > start}')
    if not project and row > start:
        print(f'  -> Would inherit main_project: {main_project}')
