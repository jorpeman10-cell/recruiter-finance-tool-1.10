"""
创建数据导入模板
"""

import pandas as pd
from datetime import datetime, timedelta
import os


def create_deals_template():
    """创建成单数据模板"""
    data = {
        'deal_id': ['D0001', 'D0002', 'D0003'],
        'client_name': ['阿里巴巴', '腾讯', '字节跳动'],
        'candidate_name': ['张三', '李四', '王五'],
        'position': ['Java开发', '产品经理', '算法工程师'],
        'consultant': ['顾问A', '顾问B', '顾问A'],
        'deal_date': ['2024-01-15', '2024-02-20', '2024-03-10'],
        'annual_salary': [500000, 600000, 800000],
        'fee_rate': [20, 20, 22],
        'fee_amount': [100000, 120000, 176000],
        'payment_status': ['已回款', '部分回款', '未回款'],
        'actual_payment': [100000, 60000, 0],
        'payment_date': ['2024-02-15', '2024-03-15', None]
    }
    return pd.DataFrame(data)


def create_consultants_template():
    """创建顾问数据模板"""
    data = {
        'name': ['顾问A', '顾问B', '顾问C'],
        'base_salary': [10000, 12000, 15000],
        'join_date': ['2023-01-15', '2023-03-01', '2022-08-20'],
        'team': ['互联网', '互联网', '金融'],
        'is_active': [True, True, True],
        'monthly_kpi': [60000, 80000, 100000]
    }
    return pd.DataFrame(data)


def create_expenses_template():
    """创建费用数据模板"""
    data = {
        'expense_id': ['E0001', 'E0002', 'E0003', 'E0004'],
        'category': ['租金', '工资', '营销', '办公'],
        'amount': [30000, 50000, 10000, 5000],
        'date': ['2024-01-01', '2024-01-01', '2024-01-15', '2024-01-20'],
        'description': ['办公室租金', '运营人员工资', '推广费用', '办公用品']
    }
    return pd.DataFrame(data)


def main():
    """生成模板文件"""
    print("正在生成数据模板...")
    
    # 创建模板目录
    template_dir = "data_templates"
    os.makedirs(template_dir, exist_ok=True)
    
    # 成单数据模板
    deals_df = create_deals_template()
    deals_df.to_excel(f"{template_dir}/成单数据模板.xlsx", index=False)
    deals_df.to_csv(f"{template_dir}/成单数据模板.csv", index=False, encoding='utf-8-sig')
    print(f"✓ 成单数据模板已生成 ({template_dir}/成单数据模板.xlsx)")
    
    # 顾问数据模板
    consultants_df = create_consultants_template()
    consultants_df.to_excel(f"{template_dir}/顾问数据模板.xlsx", index=False)
    consultants_df.to_csv(f"{template_dir}/顾问数据模板.csv", index=False, encoding='utf-8-sig')
    print(f"✓ 顾问数据模板已生成 ({template_dir}/顾问数据模板.xlsx)")
    
    # 费用数据模板
    expenses_df = create_expenses_template()
    expenses_df.to_excel(f"{template_dir}/费用数据模板.xlsx", index=False)
    expenses_df.to_csv(f"{template_dir}/费用数据模板.csv", index=False, encoding='utf-8-sig')
    print(f"✓ 费用数据模板已生成 ({template_dir}/费用数据模板.xlsx)")
    
    print("\n模板文件说明:")
    print("- 成单数据: 必须提供，包含所有成单记录")
    print("- 顾问数据: 可选，用于计算人力成本")
    print("- 费用数据: 可选，用于统计运营成本")
    print("\n使用方式:")
    print("1. 参考模板格式准备您的数据")
    print("2. 在应用侧边栏上传数据文件")
    print("3. 点击'加载上传的数据'按钮")


if __name__ == "__main__":
    main()
