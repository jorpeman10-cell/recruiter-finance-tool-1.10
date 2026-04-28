import pandas as pd

# Check sheets
xl = pd.ExcelFile('mapping_candidate_matches.xlsx')
print('Sheets:', xl.sheet_names)

# Match results
matches = pd.read_excel('mapping_candidate_matches.xlsx', sheet_name='匹配结果')
print(f"\nMatches shape: {matches.shape}")
print(f"Columns: {list(matches.columns)}")
print("\nTop 5 matches:")
print(matches.head(5).to_string())

# Unmatched
unmatched = pd.read_excel('mapping_candidate_matches.xlsx', sheet_name='未匹配节点')
print(f"\nUnmatched shape: {unmatched.shape}")

# Stats
stats = pd.read_excel('mapping_candidate_matches.xlsx', sheet_name='统计汇总')
print(f"\nStats:")
print(stats.to_string())
