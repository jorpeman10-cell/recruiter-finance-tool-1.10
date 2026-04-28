"""
Mapping组织架构图节点与系统人才数据匹配工具 V2
- 加入公司维度优先匹配
- 清洗数据质量（分类标注节点类型）
- 生成数据质量报告
"""

import sys
sys.path.insert(0, 'advanced_analysis')

import json
import pandas as pd
import numpy as np
import re
from collections import defaultdict, Counter
from gllue_db_client import GllueDBClient
import db_config_manager


# ========== 节点分类规则 ==========

def classify_node(text, note):
    """对节点进行分类，返回 (类别, 原因)"""
    text = str(text).strip() if text else ''
    note = str(note).strip() if note else ''
    combined = text + ' ' + note
    
    if not text or len(text) < 2:
        return '空节点', '文本为空或太短'
    
    lower = text.lower()
    
    # 1. 明显的垃圾数据
    if lower in ['subtopic', 'topic', 'children', 'root', 'mindmap', 'untitled']:
        return '低质数据-模板残留', '包含模板默认关键词'
    
    # 2. 纯符号/数字
    if re.match(r'^[\d\s\W]+$', text):
        return '低质数据-纯符号', '无有效文字内容'
    
    # 3. 纯英文职位缩写（常见猎头缩写）
    if re.match(r'^[A-Z]{2,6}$', text.strip()):
        return '职位缩写', '纯大写缩写如 RSM/DSM/RA'
    
    # 4. 部门/组织架构节点
    dept_keywords = ['部', '组', '中心', '委员会', '事业部', '研究院', '实验室', '科室', '办公室']
    if any(k in text for k in dept_keywords):
        if len(text) < 20:
            return '部门节点', '包含部门关键词'
    
    # 5. 纯描述性/说明文字（过长）
    if len(text) > 40:
        return '描述性文字', '长度过长，疑似说明文字'
    
    # 6. 纯英文职位（无中文）
    if re.match(r'^[A-Za-z\s]+$', text) and len(text) > 10:
        if any(w in lower for w in ['manager', 'director', 'head', 'lead', 'specialist', 'president']):
            return '英文职位', '纯英文职位描述'
    
    # 7. 数字+员工数说明
    if re.search(r'\d+\s*[\+\-]?\s*员工|人|团队', text):
        return '团队规模说明', '包含人数统计'
    
    # 8. 疑似人名
    # 模式：中英文混合 或 纯中文2-4字 或 纯英文2-3词
    has_chinese = bool(re.search(r'[^\x00-\x7F]', text))
    has_english = bool(re.search(r'[A-Za-z]{2,}', text))
    
    if has_chinese:
        # 中文名通常在2-4字，但如果包含大量中文可能是职位描述
        cn_chars = re.findall(r'[^\x00-\x7F]', text)
        if len(cn_chars) <= 8:  # 最多8个中文字符（含英文名+中文名）
            return '人名-中英文', '符合人名长度特征'
        else:
            return '职位描述', '中文过多，疑似职位描述'
    elif has_english:
        words = text.split()
        if 1 <= len(words) <= 4:
            return '人名-纯英文', '英文单词数符合人名特征'
        else:
            return '英文描述', '英文单词过多'
    
    return '其他', '无法分类'


def extract_name_candidates_v2(text):
    """从节点文本中提取可能的人名部分（V2更严格）"""
    if not text:
        return []
    candidates = []
    
    # 模式1: "English 中文" 如 "Tony 张三"
    pattern1 = re.findall(r'([A-Za-z][A-Za-z\s\.]+)\s+([^\x00-\x7F]{2,4})', text)
    for en, cn in pattern1:
        candidates.append((en.strip(), cn.strip()))
    
    # 模式2: 纯中文名 2-4字（连续中文字符）
    pattern2 = re.findall(r'[^\x00-\x7F]{2,4}', text)
    for cn in pattern2:
        # 过滤常见非人名词
        skip_words = ['医学', '临床', '研究', '开发', '管理', '总监', '经理', '主管', '专员', '总裁', '副总裁', '总经理', '负责人']
        if cn not in skip_words:
            candidates.append((None, cn.strip()))
    
    # 模式3: 纯英文名 2-4个单词
    words = text.split()
    if 1 <= len(words) <= 4 and all(w[0].isupper() or w.islower() for w in words if w):
        en_name = ' '.join(words)
        if len(en_name) >= 3:
            skip_english = ['medical', 'sales', 'manager', 'director', 'senior', 'head', 'lead', 'vp', 'ceo', 'cto', 'cfo']
            if en_name.lower() not in skip_english:
                candidates.append((en_name.strip(), None))
    
    return candidates


# ========== 主程序 ==========

def main():
    print("[1/5] Connecting to database...")
    client = GllueDBClient(db_config_manager.get_gllue_db_config())
    
    # Step 1: Extract all mapping nodes with client_id
    print("[2/5] Extracting mapping nodes...")
    mappings = client.query("""
        SELECT m.content, co.name as org_name, co.client_name, co.id as org_id, co.client_id, co.addedBy_id
        FROM companyorganizationmapping m
        JOIN companyorganization co ON m.organization_id = co.id
        WHERE m.is_current = 1 AND m.is_deleted = 0 AND co.is_deleted = 0
    """)
    
    all_nodes = []
    def extract_nodes(node, org_id, org_name, client_name, client_id, depth=0):
        text = node.get('text', '').strip()
        note = node.get('note', '').strip()
        if text or note:
            all_nodes.append({
                'org_id': org_id,
                'org_name': org_name,
                'client_name': client_name,
                'client_id': client_id,
                'text': text,
                'note': note,
                'depth': depth,
            })
        for child in node.get('children', []):
            extract_nodes(child, org_id, org_name, client_name, client_id, depth + 1)
    
    for _, row in mappings.iterrows():
        try:
            data = json.loads(row['content'])
            for root in data.get('roots', []):
                extract_nodes(root, row['org_id'], row['org_name'], row['client_name'], row['client_id'])
        except:
            pass
    
    nodes_df = pd.DataFrame(all_nodes)
    print(f"  Total nodes: {len(nodes_df)}")
    
    # Step 2: Classify all nodes
    print("[3/5] Classifying nodes...")
    classifications = []
    for _, row in nodes_df.iterrows():
        cat, reason = classify_node(row['text'], row['note'])
        classifications.append({'node_category': cat, 'node_reason': reason})
    
    class_df = pd.DataFrame(classifications)
    nodes_df = pd.concat([nodes_df.reset_index(drop=True), class_df], axis=1)
    
    print("  Category distribution:")
    cat_counts = nodes_df['node_category'].value_counts()
    for cat, cnt in cat_counts.items():
        print(f"    {cat}: {cnt}")
    
    # Step 3: Identify person nodes for matching
    person_cats = ['人名-中英文', '人名-纯英文']
    person_nodes = nodes_df[nodes_df['node_category'].isin(person_cats)].copy()
    print(f"\n  Person nodes for matching: {len(person_nodes)}")
    
    # Step 4: Load candidates with company info
    print("[4/5] Loading candidates...")
    candidates = client.query("""
        SELECT 
            c.id as candidate_id,
            CONCAT(IFNULL(c.englishName, ''), ' ', IFNULL(c.chineseName, '')) as full_name,
            c.englishName,
            c.chineseName,
            c.title,
            c.mobile,
            c.mobile1,
            c.mobile2,
            c.email,
            c.email1,
            c.email2,
            c.company_id,
            cl.name as company_name
        FROM candidate c
        LEFT JOIN client cl ON c.company_id = cl.id
        WHERE (c.englishName IS NOT NULL AND c.englishName != '')
           OR (c.chineseName IS NOT NULL AND c.chineseName != '')
        LIMIT 120000
    """)
    
    print(f"  Loaded {len(candidates)} candidates")
    
    # Build indices
    # Global indices
    global_cn = defaultdict(list)
    global_en = defaultdict(list)
    
    # Company-specific indices: company_id -> {cn: [cids], en: [cids]}
    company_cn = defaultdict(lambda: defaultdict(list))
    company_en = defaultdict(lambda: defaultdict(list))
    
    cand_lookup = {}
    
    for _, row in candidates.iterrows():
        cid = row['candidate_id']
        comp_id = row['company_id']
        cand_lookup[cid] = row
        
        if pd.notna(row['chineseName']) and str(row['chineseName']).strip():
            cn = str(row['chineseName']).strip()
            if len(cn) >= 2:
                global_cn[cn].append(cid)
                if pd.notna(comp_id):
                    company_cn[int(comp_id)][cn].append(cid)
        
        if pd.notna(row['englishName']) and str(row['englishName']).strip():
            en = str(row['englishName']).strip().lower()
            if len(en) >= 2:
                global_en[en].append(cid)
                if pd.notna(comp_id):
                    company_en[int(comp_id)][en].append(cid)
    
    # Step 5: Match
    print("[5/5] Matching with company priority...")
    
    # Extract unique person texts
    unique_persons = person_nodes.drop_duplicates(subset=['org_id', 'text'])
    
    matches = []
    matched_nodes = set()
    matched_candidates = set()
    
    for _, row in unique_persons.iterrows():
        text = row['text']
        client_id = row['client_id']
        parts = extract_name_candidates_v2(text)
        
        if not parts:
            continue
        
        matched_ids = set()
        
        # Strategy 1: Company-specific exact match (highest priority)
        if pd.notna(client_id) and client_id > 0:
            comp_id = int(client_id)
            for en, cn in parts:
                if cn and cn in company_cn[comp_id]:
                    matched_ids.update(company_cn[comp_id][cn])
                if en and isinstance(en, str) and en.lower() in company_en[comp_id]:
                    matched_ids.update(company_en[comp_id][en.lower()])
        
        # Strategy 2: Global exact match
        if not matched_ids:
            for en, cn in parts:
                if cn and cn in global_cn:
                    matched_ids.update(global_cn[cn])
                if en and isinstance(en, str) and en.lower() in global_en:
                    matched_ids.update(global_en[en.lower()])
        
        # Strategy 3: Substring match (fallback)
        if not matched_ids:
            for en, cn in parts:
                if cn:
                    for cand_cn, cids in global_cn.items():
                        if cand_cn in text:
                            matched_ids.update(cids)
        
        if matched_ids:
            # Get all node instances (same text may appear multiple times in same org)
            node_instances = person_nodes[
                (person_nodes['org_id'] == row['org_id']) & 
                (person_nodes['text'] == text)
            ]
            
            for _, node_row in node_instances.iterrows():
                for cid in matched_ids:
                    cand = cand_lookup[cid]
                    node_note = str(node_row['note'] or '').lower()
                    cand_title = str(cand['title'] or '').lower()
                    title_bonus = 0
                    if node_note and cand_title and (node_note in cand_title or cand_title in node_note):
                        title_bonus = 1
                    
                    # Check if company match
                    company_match = 0
                    if pd.notna(client_id) and pd.notna(cand['company_id']) and client_id == cand['company_id']:
                        company_match = 1
                    
                    matches.append({
                        'org_id': node_row['org_id'],
                        'org_name': node_row['org_name'],
                        'client_name': node_row['client_name'],
                        'client_id': node_row['client_id'],
                        'node_text': text,
                        'node_note': node_row['note'],
                        'node_category': node_row['node_category'],
                        'depth': node_row['depth'],
                        'candidate_id': cid,
                        'candidate_name': cand['full_name'],
                        'candidate_english': cand['englishName'],
                        'candidate_chinese': cand['chineseName'],
                        'candidate_title': cand['title'],
                        'candidate_company': cand['company_name'],
                        'candidate_mobile': cand['mobile'] or cand['mobile1'] or cand['mobile2'],
                        'candidate_email': cand['email'] or cand['email1'] or cand['email2'],
                        'company_match': company_match,
                        'title_bonus': title_bonus,
                    })
                    matched_candidates.add(cid)
                matched_nodes.add((node_row['org_id'], text))
    
    matches_df = pd.DataFrame(matches)
    if not matches_df.empty:
        matches_df = matches_df.sort_values(['company_match', 'title_bonus'], ascending=[False, False])
        matches_df = matches_df.drop_duplicates(subset=['org_id', 'node_text'], keep='first')
    
    # ========== Data Quality Analysis ==========
    print("\n[Bonus] Data quality analysis...")
    
    # Per-org quality stats
    org_stats = []
    for org_id in nodes_df['org_id'].unique():
        org_df = nodes_df[nodes_df['org_id'] == org_id]
        total = len(org_df)
        low_quality = len(org_df[org_df['node_category'].str.startswith('低质数据')])
        dept_nodes = len(org_df[org_df['node_category'] == '部门节点'])
        person_nodes_count = len(org_df[org_df['node_category'].isin(person_cats)])
        desc_nodes = len(org_df[org_df['node_category'] == '描述性文字'])
        
        org_stats.append({
            'org_id': org_id,
            'org_name': org_df['org_name'].iloc[0],
            'client_name': org_df['client_name'].iloc[0],
            'total_nodes': total,
            'person_nodes': person_nodes_count,
            'dept_nodes': dept_nodes,
            'low_quality_nodes': low_quality,
            'desc_nodes': desc_nodes,
            'person_ratio': round(person_nodes_count / total * 100, 1) if total > 0 else 0,
            'quality_score': max(0, 100 - low_quality * 5 - desc_nodes * 2),
        })
    
    org_stats_df = pd.DataFrame(org_stats).sort_values('quality_score')
    
    # Per-creator quality stats
    creator_stats = []
    creator_org = mappings[['addedBy_id', 'org_id']].drop_duplicates().merge(
        pd.DataFrame(org_stats), on='org_id', how='left'
    )
    if not creator_org.empty and 'addedBy_id' in creator_org.columns:
        for creator_id in creator_org['addedBy_id'].dropna().unique():
            c_df = creator_org[creator_org['addedBy_id'] == creator_id]
            creator_stats.append({
                'creator_id': creator_id,
                'chart_count': len(c_df),
                'avg_nodes': round(c_df['total_nodes'].mean(), 1),
                'avg_quality_score': round(c_df['quality_score'].mean(), 1),
                'total_low_quality': int(c_df['low_quality_nodes'].sum()),
            })
        creator_stats_df = pd.DataFrame(creator_stats).sort_values('avg_quality_score')
    else:
        creator_stats_df = pd.DataFrame()
    
    # ========== Export ==========
    print("\n[OK] Exporting results...")
    output_path = 'mapping_candidate_matches_v2.xlsx'
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Sheet 1: 匹配结果
        if not matches_df.empty:
            display_cols = ['client_name', 'org_name', 'node_text', 'node_note', 
                            'candidate_name', 'candidate_title', 'candidate_company',
                            'candidate_mobile', 'candidate_email', 'company_match']
            matches_df[display_cols].to_excel(writer, sheet_name='匹配结果', index=False)
        
        # Sheet 2: 未匹配人名节点
        unmatched_persons = []
        for _, row in person_nodes.iterrows():
            key = (row['org_id'], row['text'])
            if key not in matched_nodes:
                unmatched_persons.append({
                    'client_name': row['client_name'],
                    'org_name': row['org_name'],
                    'node_text': row['text'],
                    'node_note': row['note'],
                    'node_category': row['node_category'],
                })
        unmatched_df = pd.DataFrame(unmatched_persons)
        if not unmatched_df.empty:
            unmatched_df.to_excel(writer, sheet_name='未匹配人名节点', index=False)
        
        # Sheet 3: 所有节点分类
        nodes_df[['org_name', 'client_name', 'text', 'note', 'node_category', 'node_reason', 'depth']].to_excel(
            writer, sheet_name='全部节点分类', index=False)
        
        # Sheet 4: Mapping数据质量评分
        org_stats_df.to_excel(writer, sheet_name='Mapping质量评分', index=False)
        
        # Sheet 5: 录入人质量排名
        if not creator_stats_df.empty:
            creator_stats_df.to_excel(writer, sheet_name='录入人质量排名', index=False)
        
        # Sheet 6: 统计汇总
        total_person = len(person_nodes.drop_duplicates(subset=['org_id', 'text']))
        matched_count = len(matched_nodes)
        company_matched = len(matches_df[matches_df['company_match'] == 1]) if not matches_df.empty else 0
        
        stats = []
        stats.append({'指标': 'Mapping总节点数', '数值': len(nodes_df)})
        stats.append({'指标': '人名节点数', '数值': total_person})
        stats.append({'指标': '低质数据节点', '数值': len(nodes_df[nodes_df['node_category'].str.startswith('低质数据')])})
        stats.append({'指标': '描述性文字节点', '数值': len(nodes_df[nodes_df['node_category'] == '描述性文字'])})
        stats.append({'指标': '部门节点数', '数值': len(nodes_df[nodes_df['node_category'] == '部门节点'])})
        stats.append({'指标': '匹配成功节点', '数值': matched_count})
        stats.append({'指标': '其中-同公司匹配', '数值': company_matched})
        stats.append({'指标': '其中-跨公司匹配', '数值': matched_count - company_matched})
        stats.append({'指标': '匹配率', '数值': f"{matched_count/total_person*100:.1f}%" if total_person > 0 else "0%"})
        stats.append({'指标': '覆盖候选人数', '数值': len(matched_candidates)})
        stats.append({'指标': '平均数据质量分', '数值': f"{org_stats_df['quality_score'].mean():.1f}"})
        pd.DataFrame(stats).to_excel(writer, sheet_name='统计汇总', index=False)
    
    print(f"\nExport: {output_path}")
    print(f"\nSummary:")
    print(f"  Total nodes: {len(nodes_df)}")
    print(f"  Person nodes: {total_person}")
    print(f"  Low quality: {len(nodes_df[nodes_df['node_category'].str.startswith('低质数据')])}")
    print(f"  Matched: {matched_count} (company: {company_matched}, global: {matched_count - company_matched})")
    print(f"  Match rate: {matched_count/total_person*100:.1f}%" if total_person > 0 else "  Match rate: 0%")
    print(f"  Candidates covered: {len(matched_candidates)}")
    print(f"  Avg quality score: {org_stats_df['quality_score'].mean():.1f}")
    print(f"\nWorst quality Mapping (bottom 3):")
    print(org_stats_df.head(3)[['org_name', 'total_nodes', 'low_quality_nodes', 'quality_score']].to_string(index=False))


if __name__ == '__main__':
    main()
