"""
Mapping组织架构图节点与系统人才数据匹配工具
按名字+Title+电话进行匹配
"""

import sys
sys.path.insert(0, 'advanced_analysis')

import json
import pandas as pd
import numpy as np
import re
from collections import defaultdict
from gllue_db_client import GllueDBClient
import db_config_manager


def is_likely_person_name(text):
    """判断文本是否可能是人名"""
    if not text or len(text) < 2:
        return False
    if text.lower() in ['subtopic', 'topic', 'children', 'root']:
        return False
    if text.isdigit():
        return False
    if len(text) > 50:
        return False
    if re.match(r'^[A-Z]{2,8}$', text.strip()):
        return False
    dept_keywords = ['部', '组', '中心', '委员会', '事业部', '研究院', '实验室', '科室']
    if any(k in text for k in dept_keywords) and len(text) < 15:
        return False
    return True


def extract_name_candidates(text):
    """从节点文本中提取可能的人名部分"""
    if not text:
        return []
    candidates = []
    # 模式1: "English 中文" 如 "Tony 张三"
    pattern1 = re.findall(r'([A-Za-z]+)\s+([^\x00-\x7F]{2,4})', text)
    for en, cn in pattern1:
        candidates.append((en.strip(), cn.strip()))
    # 模式2: 纯中文名 2-4字
    pattern2 = re.findall(r'[^\x00-\x7F]{2,4}', text)
    for cn in pattern2:
        if cn not in ['医学', '临床', '研究', '开发', '管理', '总监', '经理', '主管', '专员']:
            candidates.append((None, cn.strip()))
    # 模式3: 纯英文名（首字母大写）
    pattern3 = re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', text)
    for en in pattern3:
        if len(en) >= 3 and en.lower() not in ['medical', 'sales', 'manager', 'director', 'senior']:
            candidates.append((en.strip(), None))
    return candidates


def main():
    print("[1/4] Connecting to database...")
    client = GllueDBClient(db_config_manager.get_gllue_db_config())
    
    # Step 1: Extract all mapping nodes
    print("[2/4] Extracting mapping nodes...")
    mappings = client.query("""
        SELECT m.content, co.name as org_name, co.client_name, co.id as org_id
        FROM companyorganizationmapping m
        JOIN companyorganization co ON m.organization_id = co.id
        WHERE m.is_current = 1 AND m.is_deleted = 0 AND co.is_deleted = 0
    """)
    
    all_nodes = []
    def extract_nodes(node, org_id, org_name, client_name, depth=0):
        text = node.get('text', '').strip()
        note = node.get('note', '').strip()
        if text:
            all_nodes.append({
                'org_id': org_id,
                'org_name': org_name,
                'client_name': client_name,
                'text': text,
                'note': note,
                'depth': depth,
            })
        for child in node.get('children', []):
            extract_nodes(child, org_id, org_name, client_name, depth + 1)
    
    for _, row in mappings.iterrows():
        try:
            data = json.loads(row['content'])
            for root in data.get('roots', []):
                extract_nodes(root, row['org_id'], row['org_name'], row['client_name'])
        except:
            pass
    
    nodes_df = pd.DataFrame(all_nodes)
    print(f"  Total nodes: {len(nodes_df)}")
    print(f"  Unique texts: {nodes_df['text'].nunique()}")
    
    # Step 2: Filter likely person names
    print("[3/4] Filtering person names...")
    nodes_df['is_person'] = nodes_df['text'].apply(is_likely_person_name)
    person_nodes = nodes_df[nodes_df['is_person']].copy()
    print(f"  Likely person nodes: {len(person_nodes)}")
    
    # Extract name parts for unique texts only
    unique_texts = person_nodes['text'].unique()
    name_lookup = {}
    for text in unique_texts:
        name_lookup[text] = extract_name_candidates(text)
    
    print(f"  Unique texts with names: {len([v for v in name_lookup.values() if v])}")
    
    # Step 3: Load candidates (efficiently)
    print("[4/4] Loading candidates and matching...")
    candidates = client.query("""
        SELECT 
            id as candidate_id,
            CONCAT(IFNULL(englishName, ''), ' ', IFNULL(chineseName, '')) as full_name,
            englishName,
            chineseName,
            title,
            mobile,
            mobile1,
            mobile2,
            email,
            email1,
            email2
        FROM candidate
        WHERE (englishName IS NOT NULL AND englishName != '')
           OR (chineseName IS NOT NULL AND chineseName != '')
        LIMIT 100000
    """)
    
    print(f"  Loaded {len(candidates)} candidates")
    
    # Build exact-match indices
    cn_to_cands = defaultdict(list)
    en_to_cands = defaultdict(list)
    
    for _, row in candidates.iterrows():
        cid = row['candidate_id']
        if pd.notna(row['chineseName']) and str(row['chineseName']).strip():
            cn = str(row['chineseName']).strip()
            if len(cn) >= 2:
                cn_to_cands[cn].append(cid)
        if pd.notna(row['englishName']) and str(row['englishName']).strip():
            en = str(row['englishName']).strip().lower()
            if len(en) >= 2:
                en_to_cands[en].append(cid)
    
    # Create candidate lookup
    cand_lookup = {}
    for _, row in candidates.iterrows():
        cand_lookup[row['candidate_id']] = row
    
    # Match: only exact matches (fast O(1) lookups)
    print("  Matching (exact match only)...")
    matches = []
    matched_nodes = set()
    matched_candidates = set()
    
    for text, parts in name_lookup.items():
        if not parts:
            continue
        
        matched_ids = set()
        for en, cn in parts:
            if cn and cn in cn_to_cands:
                matched_ids.update(cn_to_cands[cn])
            if en and isinstance(en, str) and en.lower() in en_to_cands:
                matched_ids.update(en_to_cands[en.lower()])
        
        # Also try: if any candidate chinese name appears as substring in the text
        if not matched_ids and cn:
            for cand_cn, cids in cn_to_cands.items():
                if cand_cn in text:
                    matched_ids.update(cids)
        
        if matched_ids:
            # Get node info
            node_rows = person_nodes[person_nodes['text'] == text]
            for node_idx, node_row in node_rows.iterrows():
                for cid in matched_ids:
                    cand = cand_lookup[cid]
                    node_note = str(node_row['note'] or '').lower()
                    cand_title = str(cand['title'] or '').lower()
                    title_bonus = 0
                    if node_note and cand_title and (node_note in cand_title or cand_title in node_note):
                        title_bonus = 1
                    
                    matches.append({
                        'org_id': node_row['org_id'],
                        'org_name': node_row['org_name'],
                        'client_name': node_row['client_name'],
                        'node_text': text,
                        'node_note': node_row['note'],
                        'depth': node_row['depth'],
                        'candidate_id': cid,
                        'candidate_name': cand['full_name'],
                        'candidate_english': cand['englishName'],
                        'candidate_chinese': cand['chineseName'],
                        'candidate_title': cand['title'],
                        'candidate_mobile': cand['mobile'] or cand['mobile1'] or cand['mobile2'],
                        'candidate_email': cand['email'] or cand['email1'] or cand['email2'],
                        'title_bonus': title_bonus,
                    })
                    matched_candidates.add(cid)
                matched_nodes.add((node_row['org_id'], text))
    
    matches_df = pd.DataFrame(matches)
    
    # Deduplicate: keep best match per node (by title bonus)
    if not matches_df.empty:
        matches_df = matches_df.sort_values('title_bonus', ascending=False)
        matches_df = matches_df.drop_duplicates(subset=['org_id', 'node_text'], keep='first')
    
    # Export
    print(f"\n[OK] Exporting results...")
    output_path = 'mapping_candidate_matches.xlsx'
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Sheet 1: 匹配结果
        if not matches_df.empty:
            display_cols = ['client_name', 'org_name', 'node_text', 'node_note', 
                            'candidate_name', 'candidate_title', 'candidate_mobile', 'candidate_email']
            matches_df[display_cols].to_excel(writer, sheet_name='匹配结果', index=False)
        
        # Sheet 2: 未匹配的节点
        unmatched = []
        for _, row in person_nodes.iterrows():
            key = (row['org_id'], row['text'])
            if key not in matched_nodes:
                unmatched.append({
                    'client_name': row['client_name'],
                    'org_name': row['org_name'],
                    'node_text': row['text'],
                    'node_note': row['note'],
                })
        
        unmatched_df = pd.DataFrame(unmatched)
        if not unmatched_df.empty:
            unmatched_df.to_excel(writer, sheet_name='未匹配节点', index=False)
        
        # Sheet 3: 统计汇总
        total_person_nodes = len(person_nodes.drop_duplicates(subset=['org_id', 'text']))
        matched_node_count = len(matched_nodes)
        stats = []
        stats.append({'指标': 'Mapping总节点数', '数值': len(nodes_df)})
        stats.append({'指标': '疑似人名节点数', '数值': total_person_nodes})
        stats.append({'指标': '匹配成功节点数', '数值': matched_node_count})
        stats.append({'指标': '匹配率', '数值': f"{matched_node_count/total_person_nodes*100:.1f}%" if total_person_nodes > 0 else "0%"})
        stats.append({'指标': '覆盖候选人数', '数值': len(matched_candidates)})
        pd.DataFrame(stats).to_excel(writer, sheet_name='统计汇总', index=False)
        
        # Sheet 4: 按客户统计
        if not matches_df.empty:
            client_stats = matches_df.groupby('client_name').agg({
                'node_text': 'count',
                'candidate_id': 'nunique',
            }).reset_index()
            client_stats.columns = ['客户名称', '匹配节点数', '匹配候选人数']
            client_stats = client_stats.sort_values('匹配节点数', ascending=False)
            client_stats.to_excel(writer, sheet_name='按客户统计', index=False)
    
    print(f"\nExport: {output_path}")
    print(f"\nSummary:")
    print(f"  Total nodes: {len(nodes_df)}")
    print(f"  Person nodes: {total_person_nodes}")
    print(f"  Matched: {matched_node_count}")
    print(f"  Match rate: {matched_node_count/total_person_nodes*100:.1f}%" if total_person_nodes > 0 else "  Match rate: 0%")
    print(f"  Unmatched: {len(unmatched_df)}")
    print(f"  Candidates covered: {len(matched_candidates)}")


if __name__ == '__main__':
    main()
