import pandas as pd

df = pd.read_excel('company_org_charts_summary.xlsx', sheet_name='组织架构图汇总')
print('Columns:', list(df.columns))
print('Shape:', df.shape)
print('Total charts:', len(df))
print('Avg nodes:', df['total_nodes'].mean())
print('Max depth:', df['max_depth'].max())

client_df = pd.read_excel('company_org_charts_summary.xlsx', sheet_name='按客户统计')
print('Client stats shape:', client_df.shape)
