import sys, json
sys.path.insert(0, 'advanced_analysis')
from gllue_db_client import GllueDBClient
import db_config_manager

client = GllueDBClient(db_config_manager.get_gllue_db_config())

# Extract all nodes from current mappings
print("Extracting all mapping nodes...")
mappings = client.query("""
    SELECT m.content, co.name as org_name, co.client_name
    FROM companyorganizationmapping m
    JOIN companyorganization co ON m.organization_id = co.id
    WHERE m.is_current = 1 AND m.is_deleted = 0 AND co.is_deleted = 0
""")

all_nodes = []
def extract_nodes(node, org_name, client_name):
    text = node.get('text', '').strip()
    note = node.get('note', '').strip()
    if text:
        all_nodes.append({
            'org_name': org_name,
            'client_name': client_name,
            'text': text,
            'note': note,
        })
    for child in node.get('children', []):
        extract_nodes(child, org_name, client_name)

for _, row in mappings.iterrows():
    try:
        data = json.loads(row['content'])
        for root in data.get('roots', []):
            extract_nodes(root, row['org_name'], row['client_name'])
    except:
        pass

print(f"Total nodes extracted: {len(all_nodes)}")

# Show unique text samples
import pandas as pd
df = pd.DataFrame(all_nodes)
print(f"Unique texts: {df['text'].nunique()}")
print("\nSample nodes:")
for _, row in df.drop_duplicates('text').head(20).iterrows():
    print(f"  [{row['text']}] | note=[{row['note']}]")
