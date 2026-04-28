import sys
sys.path.insert(0, 'advanced_analysis')
from gllue_db_client import GllueDBClient
import db_config_manager
from mapping_analyzer import MappingAnalyzer

client = GllueDBClient(db_config_manager.get_gllue_db_config())
analyzer = MappingAnalyzer(client)
analyzer.load_from_db()

summary = analyzer.get_summary()
print('Summary:', summary)
print()

org_df = analyzer.get_org_stats()
print('Org stats shape:', org_df.shape)
print('Org stats columns:', list(org_df.columns))
print()

creator_df = analyzer.get_creator_ranking()
print('Creator ranking shape:', creator_df.shape)
print(creator_df.head(3).to_string())
print()

cat_df = analyzer.get_category_distribution()
print('Category dist shape:', cat_df.shape)
print(cat_df.to_string())
