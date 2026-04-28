import pandas as pd

xl = pd.ExcelFile('mapping_candidate_matches_v2.xlsx')
print('Sheets:', xl.sheet_names)

# Stats
stats = pd.read_excel('mapping_candidate_matches_v2.xlsx', sheet_name='统计汇总')
print('\nStats:')
for _, row in stats.iterrows():
    print(f"  {row['指标']}: {row['数值']}")

# Quality scores
quality = pd.read_excel('mapping_candidate_matches_v2.xlsx', sheet_name='Mapping质量评分')
print(f"\nQuality stats shape: {quality.shape}")
print(f"Worst 3 quality scores:")
print(quality.nsmallest(3, 'quality_score')[['org_name', 'total_nodes', 'low_quality_nodes', 'desc_nodes', 'quality_score']].to_string())

# Category distribution
nodes = pd.read_excel('mapping_candidate_matches_v2.xlsx', sheet_name='全部节点分类')
print(f"\nNode categories:")
print(nodes['node_category'].value_counts().to_string())

# Match results
matches = pd.read_excel('mapping_candidate_matches_v2.xlsx', sheet_name='匹配结果')
print(f"\nMatches shape: {matches.shape}")
print(f"Company matches: {(matches['company_match'] == 1).sum()}")
print(matches.head(5).to_string())
