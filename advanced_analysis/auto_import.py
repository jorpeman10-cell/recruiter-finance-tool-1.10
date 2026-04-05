#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件夹自动监控与导入模块
支持轮询检测 watched/ 目录下的 Excel/CSV 文件并自动导入
"""

import os
import json
import hashlib
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional


# 支持的文件扩展名
SUPPORTED_EXTS = ('.xlsx', '.xls', '.csv')

# 导入日志文件名
IMPORT_LOG_NAME = 'import_log.json'

# 目录 -> 数据类型映射（用于路径匹配）
DIR_TYPE_MAP = {
    'deals': 'deals',
    'deal': 'deals',
    '成单': 'deals',
    'orders': 'deals',
    'consultants': 'consultants',
    'consultant': 'consultants',
    '顾问': 'consultants',
    '人员': 'consultants',
    'forecast': 'forecast',
    '预测': 'forecast',
    'real_finance': 'real_finance',
    'real': 'real_finance',
    '真实财务': 'real_finance',
    '财务状况': 'real_finance',
    'finance': 'real_finance',
    'salary': 'salary',
    '工资': 'salary',
    'reimburse': 'reimburse',
    '报销': 'reimburse',
    'fixed': 'fixed',
    '固定': 'fixed',
}

# 文件名关键词 -> 子类型映射（用于文件名匹配）
FILENAME_SUBTYPE_KEYWORDS = {
    'salary': 'salary',
    '工资': 'salary',
    '薪资': 'salary',
    '薪酬': 'salary',
    'payroll': 'salary',
    'reimburse': 'reimburse',
    '报销': 'reimburse',
    '费用': 'reimburse',
    'expense': 'reimburse',
    'fixed': 'fixed',
    '固定': 'fixed',
    '奖金': 'fixed',
    'bonus': 'fixed',
    '房租': 'fixed',
    'rent': 'fixed',
    'admin': 'fixed',
    '行政': 'fixed',
    'deal': 'deals',
    '成单': 'deals',
    '订单': 'deals',
    'placement': 'deals',
    'consultant': 'consultants',
    '顾问': 'consultants',
    '人员': 'consultants',
    'forecast': 'forecast',
    '预测': 'forecast',
}


def _get_file_fingerprint(path: str) -> str:
    """基于文件大小和修改时间生成简单指纹"""
    stat = os.stat(path)
    return f"{stat.st_size}_{stat.st_mtime}"


def _detect_file_type(rel_path: str) -> Optional[str]:
    """
    根据相对路径和文件名判断文件类型
    返回: deals | consultants | forecast | salary | reimburse | fixed | None
    """
    lower_path = rel_path.lower()
    parts = lower_path.replace('\\', '/').split('/')
    filename = parts[-1] if parts else ''
    
    # 1. 先根据文件名关键词判断（优先级最高）
    for keyword, subtype in FILENAME_SUBTYPE_KEYWORDS.items():
        if keyword in filename:
            return subtype
    
    # 2. 根据目录名判断
    for part in parts[:-1]:
        for dir_key, dir_type in DIR_TYPE_MAP.items():
            if dir_key in part:
                if dir_type == 'real_finance':
                    # 真实财务目录下如果没有文件名关键词，无法确定子类型
                    return None
                return dir_type
    
    return None


def _load_import_log(base_path: str) -> Dict:
    """加载导入日志"""
    log_path = os.path.join(base_path, IMPORT_LOG_NAME)
    if os.path.exists(log_path):
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {'files': {}}


def _save_import_log(base_path: str, log: Dict):
    """保存导入日志"""
    log_path = os.path.join(base_path, IMPORT_LOG_NAME)
    try:
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存导入日志失败: {e}")


def _is_file_locked(path: str) -> bool:
    """检查文件是否被其他进程锁定（尝试重命名到临时名）"""
    import tempfile
    tmp_path = path + '.tmpcheck'
    try:
        os.rename(path, tmp_path)
        os.rename(tmp_path, path)
        return False
    except (PermissionError, OSError):
        return True


def _read_dataframe(path: str) -> Optional[pd.DataFrame]:
    """读取 Excel 或 CSV 文件为 DataFrame"""
    try:
        lower = path.lower()
        if lower.endswith('.csv'):
            # 尝试多种编码
            for encoding in ['utf-8-sig', 'gbk', 'gb2312', 'utf-8']:
                try:
                    return pd.read_csv(path, encoding=encoding)
                except Exception:
                    continue
            return None
        else:
            return pd.read_excel(path)
    except Exception as e:
        print(f"读取文件失败 {path}: {e}")
        return None


def scan_and_import(analyzer, base_path: str) -> List[Dict]:
    """
    扫描 watched 目录并自动导入新文件
    
    Args:
        analyzer: AdvancedRecruitmentAnalyzer 实例
        base_path: watched 目录的绝对路径
    
    Returns:
        导入结果列表，每个元素包含 file, type, status, message
    """
    results = []
    
    if not os.path.exists(base_path):
        os.makedirs(base_path, exist_ok=True)
    
    log = _load_import_log(base_path)
    
    # 遍历所有文件
    for root, dirs, files in os.walk(base_path):
        # 跳过 backup 目录和临时文件
        dirs[:] = [d for d in dirs if d.lower() != 'backup']
        files = [f for f in files if f != IMPORT_LOG_NAME and not f.startswith('~$') and f.lower().endswith(SUPPORTED_EXTS)]
        # 跳过已知的旧汇总/无效文件
        files = [f for f in files if '预算' not in f and '实际' not in f]
        
        for filename in files:
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, base_path)
            fingerprint = _get_file_fingerprint(full_path)
            
            # 检查文件是否被锁定
            if _is_file_locked(full_path):
                results.append({
                    'file': rel_path,
                    'type': 'unknown',
                    'status': 'skipped',
                    'message': '文件正被其他程序使用中，请关闭后重试'
                })
                continue
            
            # 检查是否已经导入过且未变化
            existing = log['files'].get(rel_path, {})
            if existing.get('fingerprint') == fingerprint:
                continue
            
            file_type = _detect_file_type(rel_path)
            if not file_type:
                results.append({
                    'file': rel_path,
                    'type': 'unknown',
                    'status': 'skipped',
                    'message': '无法识别文件类型，请确认文件名或存放目录'
                })
                continue
            
            df = _read_dataframe(full_path)
            if df is None or df.empty:
                results.append({
                    'file': rel_path,
                    'type': file_type,
                    'status': 'failed',
                    'message': '文件读取失败或为空'
                })
                continue
            
            # 执行导入
            try:
                if file_type == 'deals':
                    analyzer.load_positions_from_dataframe(df)
                elif file_type == 'consultants':
                    analyzer.consultant_configs = {}
                    for idx, row in df.iterrows():
                        name = row.get('name')
                        if pd.notna(name):
                            salary = float(row['base_salary']) if pd.notna(row.get('base_salary')) else 20000
                            is_active = bool(row.get('is_active', True))
                            avg_positions = 6
                            if pd.notna(row.get('avg_positions')):
                                try:
                                    avg_positions = int(row['avg_positions'])
                                except Exception:
                                    pass
                            
                            join_date = None
                            for col in ['join_date', '入职日期', '入职时间', 'onboard_date']:
                                if col in row and pd.notna(row[col]):
                                    try:
                                        join_date = pd.to_datetime(row[col]).to_pydatetime()
                                    except Exception:
                                        pass
                                    if join_date:
                                        break
                            
                            leave_date = None
                            for col in ['leave_date', '离职日期', '离职时间', 'offboard_date']:
                                if col in row and pd.notna(row[col]):
                                    try:
                                        leave_date = pd.to_datetime(row[col]).to_pydatetime()
                                    except Exception:
                                        pass
                                    if leave_date:
                                        break
                            
                            analyzer.consultant_configs[name] = {
                                'monthly_salary': salary,
                                'is_active': is_active,
                                'salary_multiplier': 3.0,
                                'avg_positions': avg_positions,
                                'join_date': join_date,
                                'leave_date': leave_date,
                            }
                elif file_type == 'forecast':
                    analyzer.load_forecast_from_dataframe(df)
                elif file_type == 'salary':
                    from real_finance import load_real_salary_from_dataframe
                    records = load_real_salary_from_dataframe(df)
                    analyzer.real_cost_records.extend(records)
                elif file_type == 'reimburse':
                    from real_finance import load_real_reimburse_from_dataframe
                    records = load_real_reimburse_from_dataframe(df)
                    analyzer.real_cost_records.extend(records)
                elif file_type == 'fixed':
                    from real_finance import load_real_fixed_from_dataframe
                    records = load_real_fixed_from_dataframe(df)
                    analyzer.real_cost_records.extend(records)
                
                # 更新日志
                log['files'][rel_path] = {
                    'fingerprint': fingerprint,
                    'type': file_type,
                    'imported_at': datetime.now().isoformat(),
                    'rows': len(df)
                }
                
                results.append({
                    'file': rel_path,
                    'type': file_type,
                    'status': 'success',
                    'message': f'成功导入 {len(df)} 条记录'
                })
                
            except Exception as e:
                results.append({
                    'file': rel_path,
                    'type': file_type,
                    'status': 'failed',
                    'message': f'导入失败: {str(e)[:100]}'
                })
    
    if results:
        _save_import_log(base_path, log)
    
    return results


def get_import_history(base_path: str) -> List[Dict]:
    """获取导入历史记录"""
    log = _load_import_log(base_path)
    history = []
    for rel_path, info in log.get('files', {}).items():
        history.append({
            'file': rel_path,
            'type': info.get('type', 'unknown'),
            'imported_at': info.get('imported_at', ''),
            'rows': info.get('rows', 0)
        })
    # 按时间倒序
    history.sort(key=lambda x: x['imported_at'], reverse=True)
    return history


def clear_import_log(base_path: str):
    """清空导入日志（允许重新导入所有文件）"""
    log_path = os.path.join(base_path, IMPORT_LOG_NAME)
    if os.path.exists(log_path):
        try:
            os.remove(log_path)
        except Exception as e:
            print(f"清除导入日志失败: {e}")


def ensure_watched_dirs(base_path: str):
    """确保 watched 目录结构存在"""
    subdirs = [
        'deals',
        'consultants',
        'forecast',
        'real_finance/salary',
        'real_finance/reimburse',
        'real_finance/fixed',
    ]
    for sub in subdirs:
        os.makedirs(os.path.join(base_path, sub), exist_ok=True)
