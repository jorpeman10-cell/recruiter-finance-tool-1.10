"""
公司组织架构图(Mapping)提取工具
从Gllue数据库中提取companyorganizationmapping数据，整理为Excel
"""

import sys
sys.path.insert(0, 'advanced_analysis')

import json
import pandas as pd
from collections import Counter
from datetime import datetime
from gllue_db_client import GllueDBClient
import db_config_manager


def count_nodes(node):
    """递归计算节点数"""
    count = 1
    for child in node.get('children', []):
        count += count_nodes(child)
    return count


def get_max_depth(node, depth=1):
    """获取最大层级深度"""
    children = node.get('children', [])
    if not children:
        return depth
    return max(get_max_depth(c, depth + 1) for c in children)


def extract_all_texts(node, texts=None):
    """提取所有节点文本"""
    if texts is None:
        texts = []
    text = node.get('text', '').strip()
    if text:
        texts.append(text)
    for child in node.get('children', []):
        extract_all_texts(child, texts)
    return texts


def extract_positions(node, positions=None):
    """提取所有职位(note字段)"""
    if positions is None:
        positions = []
    note = node.get('note', '').strip()
    if note:
        positions.append(note)
    for child in node.get('children', []):
        extract_positions(child, positions)
    return positions


def main():
    print("正在连接数据库...")
    client = GllueDBClient(db_config_manager.get_gllue_db_config())
    
    # 1. 获取所有当前版本的org chart
    print("正在提取组织架构图数据...")
    df = client.query("""
        SELECT 
            co.id as org_id,
            co.name as org_name,
            co.client_name,
            co.dateAdded as created_date,
            co.lastUpdateDate as updated_date,
            co.addedBy_id,
            CONCAT(IFNULL(u.englishName, ''), ' ', IFNULL(u.chineseName, '')) as creator,
            co.joborder_name,
            m.id as mapping_id,
            m.content,
            m.dateAdded as mapping_date
        FROM companyorganization co
        JOIN companyorganizationmapping m ON co.id = m.organization_id
        LEFT JOIN user u ON co.addedBy_id = u.id
        WHERE m.is_current = 1
          AND m.is_deleted = 0
          AND co.is_deleted = 0
        ORDER BY co.lastUpdateDate DESC
    """)
    
    total = len(df)
    print(f"共找到 {total} 张当前版本组织架构图")
    
    # 2. 解析每张图的内容
    results = []
    for idx, row in df.iterrows():
        if idx % 50 == 0:
            print(f"  解析中... {idx}/{total}")
        
        content = row['content']
        if not content:
            continue
        
        try:
            data = json.loads(content)
        except:
            continue
        
        roots = data.get('roots', [])
        if not roots:
            continue
        
        # 基础统计
        total_nodes = sum(count_nodes(r) for r in roots)
        max_depth = max(get_max_depth(r) for r in roots) if roots else 0
        all_texts = []
        all_positions = []
        for r in roots:
            extract_all_texts(r, all_texts)
            extract_positions(r, all_positions)
        
        # 根节点信息
        root_texts = [r.get('text', '').strip() for r in roots]
        root_names = ' | '.join(root_texts[:3])
        
        # 职位统计
        position_counter = Counter(all_positions)
        top_positions = ', '.join([f"{k}({v})" for k, v in position_counter.most_common(5)])
        
        results.append({
            'org_id': row['org_id'],
            'org_name': row['org_name'],
            'client_name': row['client_name'],
            'creator': row['creator'],
            'created_date': row['created_date'],
            'updated_date': row['updated_date'],
            'joborder_name': row['joborder_name'],
            'total_nodes': total_nodes,
            'max_depth': max_depth,
            'root_names': root_names,
            'top_positions': top_positions,
            'all_names': ' | '.join(all_texts[:20]),  # 前20个人名
        })
    
    result_df = pd.DataFrame(results)
    print(f"成功解析 {len(result_df)} 张组织架构图")
    
    # 3. 导出Excel
    output_path = 'company_org_charts_summary.xlsx'
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Sheet 1: 汇总表
        result_df.to_excel(writer, sheet_name='组织架构图汇总', index=False)
        
        # Sheet 2: 按客户统计
        if 'client_name' in result_df.columns:
            client_stats = result_df.groupby('client_name').agg({
                'org_id': 'count',
                'total_nodes': 'sum',
                'max_depth': 'mean',
                'updated_date': 'max'
            }).reset_index()
            client_stats.columns = ['客户名称', '架构图数量', '总节点数', '平均深度', '最近更新']
            client_stats = client_stats.sort_values('架构图数量', ascending=False)
            client_stats.to_excel(writer, sheet_name='按客户统计', index=False)
        
        # Sheet 3: 按创建人统计
        if 'creator' in result_df.columns:
            creator_stats = result_df.groupby('creator').agg({
                'org_id': 'count',
                'total_nodes': 'sum',
                'updated_date': 'max'
            }).reset_index()
            creator_stats.columns = ['创建人', '架构图数量', '总节点数', '最近更新']
            creator_stats = creator_stats.sort_values('架构图数量', ascending=False)
            creator_stats.to_excel(writer, sheet_name='按创建人统计', index=False)
    
    print(f"\n[OK] 导出完成: {output_path}")
    print(f"\n数据概览:")
    print(f"  - 组织架构图总数: {len(result_df)}")
    print(f"  - 平均节点数: {result_df['total_nodes'].mean():.1f}")
    print(f"  - 最大深度: {result_df['max_depth'].max()}")
    print(f"  - 最新更新: {result_df['updated_date'].max()}")
    
    # 显示TOP 10
    print(f"\n最近更新的10张架构图:")
    top10 = result_df.nlargest(10, 'updated_date')[['org_name', 'client_name', 'creator', 'total_nodes', 'updated_date']]
    print(top10.to_string(index=False))


if __name__ == '__main__':
    main()
