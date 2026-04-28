# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
sys.path.insert(0, 'advanced_analysis')
from okr_analyzer import OKRParser

df = pd.read_excel('D:/win设备桌面/2025年业绩核算/OKR 记录/OKR-2026.3.xlsx', header=None)

# 模拟_parse_consultant中Amy的解析
start = 47
end = 57
main_project = str(df.iloc[start, 8]).strip() if pd.notna(df.iloc[start, 8]) else ''
main_target = str(df.iloc[start, 9]).strip() if pd.notna(df.iloc[start, 9]) else ''

print(f'main_project: {main_project}')
print(f'main_target: {main_target}')

for row in range(start, end):
    weight = OKRParser._to_float(df.iloc[row, 10])
    if weight <= 0:
        continue
    
    project = str(df.iloc[row, 8]).strip() if pd.notna(df.iloc[row, 8]) else ''
    target = str(df.iloc[row, 9]).strip() if pd.notna(df.iloc[row, 9]) else ''
    rule_text = str(df.iloc[row, 11]).strip() if pd.notna(df.iloc[row, 11]) else ''
    
    print(f'Row {row}: project="{project}", target="{target}"')
    
    # 如果子行没有项目名称，继承主行的
    if not project and row > start:
        # 向上查找最近的有项目的行
        for prev in range(row-1, start-1, -1):
            prev_project = str(df.iloc[prev, 8]).strip() if pd.notna(df.iloc[prev, 8]) else ''
            print(f'  Looking at Row {prev}: project="{prev_project}"')
            if prev_project:
                project = prev_project
                print(f'  -> Inherited: {project}')
                break
        if not project:
            project = main_project
            print(f'  -> Fallback to main: {project}')
    
    print(f'  Final project: {project}')
