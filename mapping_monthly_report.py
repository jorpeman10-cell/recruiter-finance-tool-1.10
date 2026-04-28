"""
Mapping 数据质量月度报告生成器
功能：
1. 提取当前所有 Mapping 数据并分类
2. 与上月历史数据对比，追踪趋势
3. 生成录入规范整改建议
4. 输出月度报告 Excel
"""

import sys
sys.path.insert(0, 'advanced_analysis')

import json
import pandas as pd
import numpy as np
import re
import os
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from gllue_db_client import GllueDBClient
import db_config_manager


# ========== 历史数据存储 ==========
HISTORY_DIR = 'mapping_history'
os.makedirs(HISTORY_DIR, exist_ok=True)


def get_history_file(month_str):
    return os.path.join(HISTORY_DIR, f'mapping_quality_{month_str}.csv')


def load_history(month_str):
    path = get_history_file(month_str)
    if os.path.exists(path):
        return pd.read_csv(path)
    return None


def save_history(df, month_str):
    path = get_history_file(month_str)
    df.to_csv(path, index=False, encoding='utf-8-sig')
    print(f"[Save] History saved: {path}")


# ========== 节点分类规则 ==========

def classify_node(text, note):
    text = str(text).strip() if text else ''
    note = str(note).strip() if note else ''
    
    if not text or len(text) < 2:
        return '空节点', '文本为空或太短'
    
    lower = text.lower()
    if lower in ['subtopic', 'topic', 'children', 'root', 'mindmap', 'untitled']:
        return '低质数据-模板残留', '包含模板默认关键词如Subtopic/Topic'
    
    if re.match(r'^[\d\s\W]+$', text):
        return '低质数据-纯符号', '无有效文字内容'
    
    if re.match(r'^[A-Z]{2,6}$', text.strip()):
        return '职位缩写', '纯大写缩写如 RSM/DSM/RA'
    
    dept_keywords = ['部', '组', '中心', '委员会', '事业部', '研究院', '实验室', '科室', '办公室']
    if any(k in text for k in dept_keywords) and len(text) < 20:
        return '部门节点', '包含部门关键词'
    
    if len(text) > 40:
        return '描述性文字', '长度过长（>40字），疑似说明文字'
    
    if re.match(r'^[A-Za-z\s]+$', text) and len(text) > 10:
        if any(w in lower for w in ['manager', 'director', 'head', 'lead', 'specialist', 'president']):
            return '英文职位', '纯英文职位描述'
    
    if re.search(r'\d+\s*[\+\-]?\s*(员工|人|团队)', text):
        return '团队规模说明', '包含人数统计如"300+员工"'
    
    has_chinese = bool(re.search(r'[^\x00-\x7F]', text))
    has_english = bool(re.search(r'[A-Za-z]{2,}', text))
    
    if has_chinese:
        cn_chars = re.findall(r'[^\x00-\x7F]', text)
        if len(cn_chars) <= 8:
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


# ========== 整改建议生成器 ==========

def generate_recommendation(categories, low_quality_count, desc_count):
    recs = []
    cat_set = set(categories)
    
    if '低质数据-模板残留' in cat_set:
        recs.append("删除所有 'Subtopic' / 'Topic' 等模板默认节点，替换为实际人名或职位")
    
    if '低质数据-纯符号' in cat_set:
        recs.append("删除纯数字/纯符号节点，补充完整人名信息")
    
    if desc_count > 0:
        recs.append(f"将 {desc_count} 个过长描述节点拆分为：人名 + 职位（分开两个节点）")
    
    if '低质数据-描述性' in cat_set:
        recs.append("避免在节点中粘贴大段说明文字，建议放入备注(note)字段")
    
    if '职位缩写' in cat_set:
        recs.append("职位缩写节点建议补充完整：如'RSM'改为'张三 RSM'，便于后续人才匹配")
    
    if '英文职位' in cat_set or '职位描述' in cat_set:
        recs.append("纯职位描述节点建议补充具体人名，或标注'待补充'状态")
    
    if '团队规模说明' in cat_set:
        recs.append("团队规模信息建议放入根节点备注，不要作为独立子节点")
    
    if not recs:
        recs.append("数据质量良好，继续保持")
    
    return "；".join(recs)


# ========== 主程序 ==========

def main():
    today = datetime.now()
    current_month = today.strftime('%Y-%m')
    last_month = (today - timedelta(days=30)).strftime('%Y-%m')
    
    print(f"=== Mapping 数据质量月度报告 ===")
    print(f"报告月份: {current_month}")
    print(f"对比月份: {last_month}")
    print()
    
    # Step 1: Extract
    print("[1/4] Extracting mapping data...")
    client = GllueDBClient(db_config_manager.get_gllue_db_config())
    
    mappings = client.query("""
        SELECT m.content, co.name as org_name, co.client_name, co.id as org_id, 
               co.client_id, co.addedBy_id, co.dateAdded, co.lastUpdateDate,
               CONCAT(IFNULL(u.englishName, ''), ' ', IFNULL(u.chineseName, '')) as creator_name
        FROM companyorganizationmapping m
        JOIN companyorganization co ON m.organization_id = co.id
        LEFT JOIN user u ON co.addedBy_id = u.id
        WHERE m.is_current = 1 AND m.is_deleted = 0 AND co.is_deleted = 0
    """)
    
    print(f"  Current mappings: {len(mappings)}")
    
    # Step 2: Parse all nodes
    print("[2/4] Parsing and classifying nodes...")
    all_nodes = []
    org_records = []
    
    for _, row in mappings.iterrows():
        org_id = row['org_id']
        org_name = row['org_name']
        client_name = row['client_name']
        creator = row['creator_name']
        
        try:
            data = json.loads(row['content'])
        except:
            continue
        
        def extract_nodes(node, depth=0):
            text = node.get('text', '').strip()
            note = node.get('note', '').strip()
            if text or note:
                cat, reason = classify_node(text, note)
                all_nodes.append({
                    'org_id': org_id,
                    'org_name': org_name,
                    'client_name': client_name,
                    'creator': creator,
                    'text': text,
                    'note': note,
                    'category': cat,
                    'reason': reason,
                    'depth': depth,
                })
            for child in node.get('children', []):
                extract_nodes(child, depth + 1)
        
        for root in data.get('roots', []):
            extract_nodes(root)
        
        # Org-level stats
        org_df = pd.DataFrame([n for n in all_nodes if n['org_id'] == org_id])
        if len(org_df) > 0:
            total = len(org_df)
            low_q = len(org_df[org_df['category'].str.startswith('低质数据')])
            desc = len(org_df[org_df['category'] == '描述性文字'])
            person = len(org_df[org_df['category'].isin(['人名-中英文', '人名-纯英文'])])
            cats = org_df['category'].tolist()
            
            org_records.append({
                'month': current_month,
                'org_id': org_id,
                'org_name': org_name,
                'client_name': client_name,
                'creator': creator,
                'total_nodes': total,
                'person_nodes': person,
                'low_quality_nodes': low_q,
                'desc_nodes': desc,
                'quality_score': max(0, 100 - low_q * 5 - desc * 2),
                'recommendation': generate_recommendation(cats, low_q, desc),
            })
    
    current_df = pd.DataFrame(org_records)
    print(f"  Total nodes parsed: {len(all_nodes)}")
    print(f"  Orgs analyzed: {len(current_df)}")
    
    # Step 3: Compare with history
    print("[3/4] Comparing with history...")
    history_df = load_history(last_month)
    
    comparison_results = []
    if history_df is not None and not history_df.empty:
        print(f"  Loaded history: {len(history_df)} orgs from {last_month}")
        
        # Merge current vs last month
        merged = current_df.merge(
            history_df[['org_id', 'total_nodes', 'quality_score', 'low_quality_nodes']],
            on='org_id', how='outer', suffixes=('_current', '_last')
        )
        
        for _, row in merged.iterrows():
            is_new = pd.isna(row.get('total_nodes_last'))
            is_deleted = pd.isna(row.get('total_nodes_current'))
            
            if is_new:
                trend = '新增'
                node_change = row['total_nodes_current']
                score_change = 0
            elif is_deleted:
                trend = '已删除'
                node_change = -row['total_nodes_last']
                score_change = 0
            else:
                node_change = row['total_nodes_current'] - row['total_nodes_last']
                score_change = row['quality_score_current'] - row['quality_score_last']
                if node_change > 5:
                    trend = '扩容'
                elif node_change < -5:
                    trend = '缩减'
                elif score_change > 5:
                    trend = '质量提升'
                elif score_change < -5:
                    trend = '质量下降'
                else:
                    trend = '稳定'
            
            comparison_results.append({
                'org_id': row['org_id'],
                'org_name': row.get('org_name', ''),
                'client_name': row.get('client_name', ''),
                'creator': row.get('creator', ''),
                'trend': trend,
                'node_change': node_change if not is_deleted else None,
                'score_change': score_change if not is_new and not is_deleted else None,
                'current_nodes': row.get('total_nodes_current', 0),
                'current_score': row.get('quality_score_current', 0),
                'last_nodes': row.get('total_nodes_last', 0),
                'last_score': row.get('quality_score_last', 0),
                'recommendation': row.get('recommendation', ''),
            })
    else:
        print(f"  No history found for {last_month}, generating baseline report")
        for _, row in current_df.iterrows():
            comparison_results.append({
                'org_id': row['org_id'],
                'org_name': row['org_name'],
                'client_name': row['client_name'],
                'creator': row['creator'],
                'trend': '基线',
                'node_change': None,
                'score_change': None,
                'current_nodes': row['total_nodes'],
                'current_score': row['quality_score'],
                'last_nodes': None,
                'last_score': None,
                'recommendation': row['recommendation'],
            })
    
    comparison_df = pd.DataFrame(comparison_results)
    
    # Step 4: Generate creator-level report
    print("[4/4] Generating reports...")
    
    creator_report = []
    for creator in comparison_df['creator'].dropna().unique():
        c_df = comparison_df[comparison_df['creator'] == creator]
        creator_report.append({
            '录入人': creator,
            'Mapping数量': len(c_df),
            '平均质量分': round(c_df['current_score'].mean(), 1),
            '最低质量分': c_df['current_score'].min(),
            '低质Mapping数': len(c_df[c_df['current_score'] < 60]),
            '新增数': len(c_df[c_df['trend'] == '新增']),
            '质量下降数': len(c_df[c_df['trend'] == '质量下降']),
            '待整改建议': '；'.join(c_df[c_df['current_score'] < 60]['recommendation'].unique()[:3]),
        })
    
    creator_df = pd.DataFrame(creator_report).sort_values('平均质量分')
    
    # Category distribution
    nodes_df = pd.DataFrame(all_nodes)
    cat_dist = nodes_df['category'].value_counts().reset_index()
    cat_dist.columns = ['节点类型', '数量']
    cat_dist['占比'] = (cat_dist['数量'] / len(nodes_df) * 100).round(1).astype(str) + '%'
    
    # Export
    output_file = f'Mapping_Monthly_Report_{current_month}.xlsx'
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Sheet 1: 月度对比（主报告）
        display_cols = ['org_name', 'client_name', 'creator', 'trend', 
                        'current_nodes', 'current_score', 'node_change', 'score_change',
                        'recommendation']
        comparison_df[display_cols].to_excel(writer, sheet_name='月度对比', index=False)
        
        # Sheet 2: 录入人质量排名
        creator_df.to_excel(writer, sheet_name='录入人质量排名', index=False)
        
        # Sheet 3: 节点类型分布
        cat_dist.to_excel(writer, sheet_name='节点类型分布', index=False)
        
        # Sheet 4: 低质量 Mapping 清单（需整改）
        low_quality = comparison_df[comparison_df['current_score'] < 60].sort_values('current_score')
        low_quality[['org_name', 'client_name', 'creator', 'current_score', 
                     'current_nodes', 'recommendation']].to_excel(
            writer, sheet_name='待整改清单', index=False)
        
        # Sheet 5: 本月新增 Mapping
        new_mappings = comparison_df[comparison_df['trend'] == '新增']
        if not new_mappings.empty:
            new_mappings[['org_name', 'client_name', 'creator', 'current_nodes', 
                         'current_score']].to_excel(writer, sheet_name='本月新增', index=False)
        
        # Sheet 6: 统计汇总
        total_orgs = len(current_df)
        total_nodes = len(nodes_df)
        person_nodes = len(nodes_df[nodes_df['category'].isin(['人名-中英文', '人名-纯英文'])])
        low_q_nodes = len(nodes_df[nodes_df['category'].str.startswith('低质数据')])
        avg_score = current_df['quality_score'].mean()
        
        summary_data = [
            {'指标': '报告月份', '数值': current_month},
            {'指标': '对比月份', '数值': last_month if history_df is not None else '无'},
            {'指标': 'Mapping总数', '数值': total_orgs},
            {'指标': '总节点数', '数值': total_nodes},
            {'指标': '人名节点数', '数值': person_nodes},
            {'指标': '低质数据节点', '数值': low_q_nodes},
            {'指标': '平均质量分', '数值': f'{avg_score:.1f}'},
            {'指标': '需整改Mapping数', '数值': len(low_quality)},
            {'指标': '新增Mapping数', '数值': len(new_mappings)},
            {'指标': '质量下降数', '数值': len(comparison_df[comparison_df['trend'] == '质量下降'])},
        ]
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='统计汇总', index=False)
    
    # Save history for next month
    save_history(current_df[['month', 'org_id', 'org_name', 'client_name', 'creator',
                              'total_nodes', 'person_nodes', 'low_quality_nodes', 
                              'desc_nodes', 'quality_score']], current_month)
    
    print(f"\n[OK] Report exported: {output_file}")
    print(f"\nSummary:")
    print(f"  Total orgs: {total_orgs}")
    print(f"  Total nodes: {total_nodes}")
    print(f"  Person nodes: {person_nodes}")
    print(f"  Low quality: {low_q_nodes}")
    print(f"  Avg score: {avg_score:.1f}")
    print(f"  Need fix: {len(low_quality)}")
    print(f"  New this month: {len(new_mappings)}")
    print(f"  Score dropped: {len(comparison_df[comparison_df['trend'] == '质量下降'])}")
    
    if not creator_df.empty:
        print(f"\nBottom 3 creators by quality:")
        print(creator_df.head(3)[['录入人', 'Mapping数量', '平均质量分', '低质Mapping数']].to_string(index=False))


if __name__ == '__main__':
    main()
