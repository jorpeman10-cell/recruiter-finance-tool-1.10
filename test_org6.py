import sys, json
sys.path.insert(0, 'advanced_analysis')
from gllue_db_client import GllueDBClient
import db_config_manager

client = GllueDBClient(db_config_manager.get_gllue_db_config())

# Parse a few samples to understand meta structure
print("=== Analyzing 3 samples ===")
r = client.query("""
    SELECT m.content, co.name, co.client_name, m.dateAdded
    FROM companyorganizationmapping m
    JOIN companyorganization co ON m.organization_id = co.id
    WHERE m.content IS NOT NULL AND m.content != '' AND m.is_deleted = 0 AND m.is_current = 1
    ORDER BY m.dateAdded DESC
    LIMIT 3
""")

for idx, row in r.iterrows():
    print(f"\n--- Sample {idx+1}: {row['name']} (client: {row['client_name']}) ---")
    try:
        data = json.loads(row['content'])
        
        def analyze_node(node, depth=0):
            prefix = "  " * depth
            text = node.get('text', '').strip()
            note = node.get('note', '').strip()
            meta = node.get('meta', '')
            node_type = node.get('type', '')
            
            info = f"{prefix}{text}"
            if note:
                info += f" [{note}]"
            if meta:
                try:
                    meta_obj = json.loads(meta)
                    if 'userId' in meta_obj:
                        info += f" (userId:{meta_obj['userId']})"
                    if 'type' in meta_obj:
                        info += f" type:{meta_obj['type']}"
                except:
                    pass
            print(info)
            
            for child in node.get('children', []):
                analyze_node(child, depth + 1)
        
        for root in data.get('roots', []):
            analyze_node(root)
            
    except Exception as e:
        print(f"Error: {e}")

# Check if meta links to candidates in the system
print("\n=== Checking meta userId links ===")
r2 = client.query("""
    SELECT m.content
    FROM companyorganizationmapping m
    WHERE m.content LIKE '%userId%' AND m.is_deleted = 0 AND m.is_current = 1
    LIMIT 5
""")
user_ids = set()
for _, row in r2.iterrows():
    try:
        data = json.loads(row['content'])
        def extract_user_ids(node):
            meta = node.get('meta', '')
            if meta:
                try:
                    meta_obj = json.loads(meta)
                    if 'userId' in meta_obj:
                        user_ids.add(meta_obj['userId'])
                except:
                    pass
            for child in node.get('children', []):
                extract_user_ids(child)
        for root in data.get('roots', []):
            extract_user_ids(root)
    except:
        pass

print(f"Found userIds: {user_ids}")
if user_ids:
    ids_str = ','.join(str(u) for u in list(user_ids)[:10])
    r3 = client.query(f"""
        SELECT id, englishName, chineseName, email
        FROM user
        WHERE id IN ({ids_str})
    """)
    print("Linked users:")
    print(r3.to_string())
