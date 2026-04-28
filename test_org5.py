import sys, json
sys.path.insert(0, 'advanced_analysis')
from gllue_db_client import GllueDBClient
import db_config_manager

client = GllueDBClient(db_config_manager.get_gllue_db_config())

# Count total mappings
print("=== companyorganizationmapping stats ===")
r = client.query("""
    SELECT 
        COUNT(*) as total,
        COUNT(DISTINCT organization_id) as unique_orgs,
        SUM(CASE WHEN is_current = 1 THEN 1 ELSE 0 END) as current_versions,
        SUM(CASE WHEN content IS NOT NULL AND content != '' THEN 1 ELSE 0 END) as with_content
    FROM companyorganizationmapping
    WHERE is_deleted = 0
""")
print(r.to_string())

# Get a sample with full content
print("\n=== Sample content structure ===")
r2 = client.query("""
    SELECT m.id, m.organization_id, m.is_current, m.dateAdded,
           co.name as org_name, co.client_name
    FROM companyorganizationmapping m
    JOIN companyorganization co ON m.organization_id = co.id
    WHERE m.content IS NOT NULL AND m.content != '' AND m.is_deleted = 0
    ORDER BY m.dateAdded DESC
    LIMIT 5
""")
print(r2.to_string())

# Parse one sample to understand structure
print("\n=== Parsing one sample ===")
r3 = client.query("""
    SELECT m.content, co.name, co.client_name
    FROM companyorganizationmapping m
    JOIN companyorganization co ON m.organization_id = co.id
    WHERE m.content IS NOT NULL AND m.content != '' AND m.is_deleted = 0
    ORDER BY m.dateAdded DESC
    LIMIT 1
""")
if not r3.empty:
    content = r3.iloc[0]['content']
    name = r3.iloc[0]['name']
    client_name = r3.iloc[0]['client_name']
    print(f"Org: {name}, Client: {client_name}")
    print(f"Content length: {len(content)}")
    try:
        data = json.loads(content)
        print(f"Top-level keys: {list(data.keys())}")
        if 'roots' in data:
            print(f"Number of roots: {len(data['roots'])}")
            if data['roots']:
                root = data['roots'][0]
                print(f"Root keys: {list(root.keys())}")
                print(f"Root text: {root.get('text', 'N/A')}")
                print(f"Root children count: {len(root.get('children', []))}")
                
                # Count total nodes recursively
                def count_nodes(node):
                    count = 1
                    for child in node.get('children', []):
                        count += count_nodes(child)
                    return count
                
                total_nodes = sum(count_nodes(r) for r in data['roots'])
                print(f"Total nodes in diagram: {total_nodes}")
    except Exception as e:
        print(f"Parse error: {e}")
        print(f"Raw content preview: {content[:500]}")
