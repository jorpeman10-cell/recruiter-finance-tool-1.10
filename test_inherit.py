# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
df = pd.read_excel('D:/win设备桌面/2025年业绩核算/OKR 记录/OKR-2026.3.xlsx', header=None)

# Amy的行 47-56
start = 47
end = 57
for row in range(start, end):
    project = str(df.iloc[row, 8]).strip() if pd.notna(df.iloc[row, 8]) else ''
    weight = df.iloc[row, 10] if pd.notna(df.iloc[row, 10]) else 0
    if weight > 0:
        print(f'Row {row}: project="{project}"')
        if not project and row > start:
            # 向上查找
            for prev in range(row-1, start-1, -1):
                prev_project = str(df.iloc[prev, 8]).strip() if pd.notna(df.iloc[prev, 8]) else ''
                print(f'  Looking at Row {prev}: project="{prev_project}"')
                if prev_project:
                    print(f'  -> Inherited: {prev_project}')
                    break
