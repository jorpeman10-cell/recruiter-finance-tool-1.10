import pandas as pd

file = 'Mapping_Monthly_Report_2026-04.xlsx'
xl = pd.ExcelFile(file)
print('Sheets:', xl.sheet_names)

# Summary
summary = pd.read_excel(file, sheet_name='统计汇总')
print('\nSummary:')
for _, row in summary.iterrows():
    print(f"  {row['指标']}: {row['数值']}")

# Creator ranking
creators = pd.read_excel(file, sheet_name='录入人质量排名')
print(f"\nCreator ranking shape: {creators.shape}")
print("Top 5 worst creators:")
print(creators.head(5).to_string())

# Low quality list
lowq = pd.read_excel(file, sheet_name='待整改清单')
print(f"\nLow quality shape: {lowq.shape}")
print("First 3 to fix:")
print(lowq.head(3).to_string())

# Category distribution
cat = pd.read_excel(file, sheet_name='节点类型分布')
print(f"\nCategory distribution:")
print(cat.to_string())
