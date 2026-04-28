import pandas as pd

# Read the summary sheet
df = pd.read_excel('company_org_charts_summary.xlsx', sheet_name='组织架构图汇总')
print('Columns:', list(df.columns))
print()
print('Shape:', df.shape)
print()
print('First 3 rows:')
print(df.head(3).to_string())
print()
print('Stats:')
print(f'  Total charts: {len(df)}')
print(f'  Avg nodes: {df["total_nodes"].mean():.1f}')
print(f'  Max depth: {df["max_depth"].max()}')
print()

# Read client stats
client_df = pd.read_excel('company_org_charts_summary.xlsx', sheet_name='按客户统计')
print('Top 10 clients by chart count:')
print(client_df.head(10).to_string())
