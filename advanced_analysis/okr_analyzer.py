"""
OKR 分析和绩效工资计算模块
支持从Excel导入OKR数据，并与系统实时数据对比
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json
import re


@dataclass
class OKRIndicator:
    """OKR单项指标"""
    name: str  # 考核项目名称
    target: str  # 考核指标描述
    weight: float  # 计算权重
    rule: str  # 起算标准/计算规则
    actual: float  # 实际完成值
    bonus: float  # 实得奖金
    
    @property
    def completion_rate(self) -> float:
        """完成率（根据指标类型计算）"""
        if not self.target or pd.isna(self.actual):
            return 0.0
        
        # 尝试从target中提取数字目标
        numbers = re.findall(r'(\d+\.?\d*)', str(self.target))
        if numbers:
            try:
                target_val = float(numbers[0])
                if target_val > 0:
                    return min(self.actual / target_val, 2.0)  # 最高200%
            except:
                pass
        return 0.0


@dataclass
class ConsultantOKR:
    """顾问月度OKR记录"""
    consultant_name: str  # 顾问英文名
    chinese_name: str  # 中文名
    level: str  # 级别 (PCII, AD, SCI, SM, etc.)
    team: str  # RA/团队
    manager: str  # 汇报线
    join_date: Optional[datetime]  # 入职日期
    probation_end: Optional[datetime]  # 试用期至
    
    # OKR指标列表
    indicators: List[OKRIndicator] = field(default_factory=list)
    
    # 月度汇总
    month_bonus: float = 0.0  # 当月奖金合计
    prev_month_adjustment: float = 0.0  # 上月待补发奖金
    total_bonus: float = 0.0  # 总发奖金
    
    # 月份标识
    year: int = 2026
    month: int = 3
    
    @property
    def total_weight(self) -> float:
        """总权重"""
        return sum(i.weight for i in self.indicators if pd.notna(i.weight))
    
    @property
    def total_bonus_calculated(self) -> float:
        """根据指标计算的奖金总和"""
        return sum(i.bonus for i in self.indicators if pd.notna(i.bonus))
    
    @property
    def avg_completion(self) -> float:
        """平均完成率"""
        rates = [i.completion_rate for i in self.indicators if i.completion_rate > 0]
        return np.mean(rates) if rates else 0.0
    
    @property
    def is_probation(self) -> bool:
        """是否在试用期"""
        if not self.probation_end:
            return False
        today = datetime.now()
        return today <= self.probation_end


class OKRDataLoader:
    """OKR数据加载器 - 从Excel解析OKR表格"""
    
    # 列映射（基于OKR-2026.3.xlsx的结构）
    COL_EN_NAME = 1
    COL_CN_NAME = 2
    COL_LEVEL = 3
    COL_TEAM = 4
    COL_MANAGER = 5
    COL_JOIN_DATE = 6
    COL_PROBATION = 7
    COL_PROJECT = 8
    COL_TARGET = 9
    COL_WEIGHT = 10
    COL_RULE = 11
    COL_ACTUAL = 12
    COL_BONUS = 13
    COL_MONTH_BONUS = 14
    COL_PREV_ADJUST = 15
    COL_TOTAL_BONUS = 16
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.raw_df = None
        self.consultant_okrs: List[ConsultantOKR] = []
    
    def parse(self) -> List[ConsultantOKR]:
        """解析Excel文件"""
        # 读取原始数据（无header）
        self.raw_df = pd.read_excel(self.file_path, header=None)
        
        # 找出所有顾问行（有英文名字的行）
        name_rows = []
        for i in range(len(self.raw_df)):
            val = self.raw_df.iloc[i, self.COL_EN_NAME]
            if (pd.notna(val) and 
                val != '英文名字' and 
                isinstance(val, str) and 
                len(val) > 1 and 
                val not in ['NaN', 'nan']):
                name_rows.append(i)
        
        # 解析每个顾问的OKR
        for i, idx in enumerate(name_rows):
            next_idx = name_rows[i+1] if i+1 < len(name_rows) else len(self.raw_df)
            okr = self._parse_consultant(idx, next_idx)
            if okr:
                self.consultant_okrs.append(okr)
        
        return self.consultant_okrs
    
    def _parse_consultant(self, start_row: int, end_row: int) -> Optional[ConsultantOKR]:
        """解析单个顾问的OKR数据"""
        df = self.raw_df
        
        # 基本信息
        en_name = df.iloc[start_row, self.COL_EN_NAME]
        cn_name = df.iloc[start_row, self.COL_CN_NAME]
        
        if pd.isna(en_name) or en_name == '英文名字':
            return None
        
        # 解析日期
        join_date = self._parse_date(df.iloc[start_row, self.COL_JOIN_DATE])
        probation_end = self._parse_date(df.iloc[start_row, self.COL_PROBATION])
        
        # 创建顾问OKR对象
        okr = ConsultantOKR(
            consultant_name=str(en_name).strip(),
            chinese_name=str(cn_name).strip() if pd.notna(cn_name) else '',
            level=str(df.iloc[start_row, self.COL_LEVEL]).strip() if pd.notna(df.iloc[start_row, self.COL_LEVEL]) else '',
            team=str(df.iloc[start_row, self.COL_TEAM]).strip() if pd.notna(df.iloc[start_row, self.COL_TEAM]) else '',
            manager=str(df.iloc[start_row, self.COL_MANAGER]).strip() if pd.notna(df.iloc[start_row, self.COL_MANAGER]) else '',
            join_date=join_date,
            probation_end=probation_end,
            month_bonus=self._parse_number(df.iloc[start_row, self.COL_MONTH_BONUS]),
            prev_month_adjustment=self._parse_number(df.iloc[start_row, self.COL_PREV_ADJUST]),
            total_bonus=self._parse_number(df.iloc[start_row, self.COL_TOTAL_BONUS]),
        )
        
        # 解析OKR指标（包括主行和子行）
        for row_idx in range(start_row, end_row):
            weight = self._parse_number(df.iloc[row_idx, self.COL_WEIGHT])
            if pd.isna(weight) or weight == 0:
                continue
            
            # 主行有项目名称，子行可能没有
            project = df.iloc[row_idx, self.COL_PROJECT]
            target = df.iloc[row_idx, self.COL_TARGET]
            
            # 如果子行没有项目名称，使用主行的
            if pd.isna(project) and row_idx == start_row:
                project = ''
            elif pd.isna(project):
                # 尝试从主行获取
                project = df.iloc[start_row, self.COL_PROJECT]
            
            indicator = OKRIndicator(
                name=str(project).strip() if pd.notna(project) else '',
                target=str(target).strip() if pd.notna(target) else '',
                weight=weight,
                rule=str(df.iloc[row_idx, self.COL_RULE]).strip() if pd.notna(df.iloc[row_idx, self.COL_RULE]) else '',
                actual=self._parse_number(df.iloc[row_idx, self.COL_ACTUAL]),
                bonus=self._parse_number(df.iloc[row_idx, self.COL_BONUS]),
            )
            okr.indicators.append(indicator)
        
        return okr
    
    def _parse_date(self, val) -> Optional[datetime]:
        """解析日期"""
        if pd.isna(val):
            return None
        try:
            return pd.to_datetime(val)
        except:
            return None
    
    def _parse_number(self, val) -> float:
        """解析数字"""
        if pd.isna(val):
            return 0.0
        try:
            return float(val)
        except:
            return 0.0
    
    def to_dataframe(self) -> pd.DataFrame:
        """转换为DataFrame（用于展示）"""
        rows = []
        for okr in self.consultant_okrs:
            for indicator in okr.indicators:
                rows.append({
                    '顾问': okr.consultant_name,
                    '中文名': okr.chinese_name,
                    '级别': okr.level,
                    '团队': okr.team,
                    '汇报线': okr.manager,
                    '考核项目': indicator.name,
                    '考核指标': indicator.target,
                    '权重': indicator.weight,
                    '实际完成': indicator.actual,
                    '实得奖金': indicator.bonus,
                    '完成率': indicator.completion_rate,
                    '月度奖金合计': okr.month_bonus,
                    '上月补发': okr.prev_month_adjustment,
                    '总发奖金': okr.total_bonus,
                })
        return pd.DataFrame(rows)
    
    def get_summary_df(self) -> pd.DataFrame:
        """获取顾问汇总DataFrame"""
        rows = []
        for okr in self.consultant_okrs:
            rows.append({
                '顾问': okr.consultant_name,
                '中文名': okr.chinese_name,
                '级别': okr.level,
                '团队': okr.team,
                '汇报线': okr.manager,
                '指标数': len(okr.indicators),
                '总权重': okr.total_weight,
                '平均完成率': okr.avg_completion,
                '月度奖金': okr.month_bonus,
                '上月补发': okr.prev_month_adjustment,
                '总发奖金': okr.total_bonus,
            })
        return pd.DataFrame(rows)


class OKRAnalyzer:
    """OKR分析器 - 对比系统实时数据"""
    
    def __init__(self, okr_loader: OKRDataLoader):
        self.okr_loader = okr_loader
        self.db_client = None
    
    def set_db_client(self, db_client):
        """设置数据库客户端（用于同步实时数据）"""
        self.db_client = db_client
    
    def get_system_stats(self, consultant_name: str, year: int, month: int) -> Dict:
        """
        从数据库获取顾问的实时业务数据
        
        Returns:
            {
                'cvsent_count': 推荐数,
                'interview_count': 面试数,
                'offer_count': Offer数,
                'offer_amount': Offer金额,
                'invoice_amount': 回款金额,
                'new_jobs': 新增职位数,
            }
        """
        if not self.db_client:
            return {}
        
        # 构建月份日期范围
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year+1}-01-01"
        else:
            end_date = f"{year}-{month+1:02d}-01"
        
        # 获取顾问ID（通过名字匹配）
        user_sql = f"""
            SELECT id FROM user 
            WHERE englishName LIKE '%{consultant_name}%' 
               OR chineseName LIKE '%{consultant_name}%'
            LIMIT 1
        """
        user_df = self.db_client.query(user_sql)
        if user_df.empty:
            return {}
        
        user_id = user_df.iloc[0]['id']
        
        # 查询各项业务数据
        stats = {}
        
        # 1. 推荐数
        cv_sql = f"""
            SELECT COUNT(*) as cnt FROM cvsent 
            WHERE user_id = {user_id} 
              AND dateAdded >= '{start_date}' 
              AND dateAdded < '{end_date}'
              AND active = 1
        """
        cv_df = self.db_client.query(cv_sql)
        stats['cvsent_count'] = int(cv_df.iloc[0]['cnt']) if not cv_df.empty else 0
        
        # 2. 面试数
        int_sql = f"""
            SELECT COUNT(*) as cnt FROM clientinterview ci
            JOIN jobsubmission js ON ci.jobsubmission_id = js.id
            WHERE js.user_id = {user_id}
              AND ci.date >= '{start_date}'
              AND ci.date < '{end_date}'
              AND ci.active = 1
        """
        int_df = self.db_client.query(int_sql)
        stats['interview_count'] = int(int_df.iloc[0]['cnt']) if not int_df.empty else 0
        
        # 3. Offer数
        offer_sql = f"""
            SELECT COUNT(*) as cnt, SUM(revenue) as amount 
            FROM offersign 
            WHERE user_id = {user_id}
              AND signDate >= '{start_date}'
              AND signDate < '{end_date}'
              AND active = 1
        """
        offer_df = self.db_client.query(offer_sql)
        stats['offer_count'] = int(offer_df.iloc[0]['cnt']) if not offer_df.empty else 0
        stats['offer_amount'] = float(offer_df.iloc[0]['amount']) if not offer_df.empty and pd.notna(offer_df.iloc[0]['amount']) else 0
        
        # 4. 回款金额
        inv_sql = f"""
            SELECT SUM(revenue) as amount 
            FROM invoiceassignment 
            WHERE user_id = {user_id}
        """
        inv_df = self.db_client.query(inv_sql)
        stats['invoice_amount'] = float(inv_df.iloc[0]['amount']) if not inv_df.empty and pd.notna(inv_df.iloc[0]['amount']) else 0
        
        # 5. 新增职位数
        job_sql = f"""
            SELECT COUNT(*) as cnt FROM joborder
            WHERE addedBy_id = {user_id}
              AND dateAdded >= '{start_date}'
              AND dateAdded < '{end_date}'
              AND is_deleted = 0
        """
        job_df = self.db_client.query(job_sql)
        stats['new_jobs'] = int(job_df.iloc[0]['cnt']) if not job_df.empty else 0
        
        return stats
    
    def compare_with_system(self, year: int = 2026, month: int = 3) -> pd.DataFrame:
        """
        对比OKR目标与系统实际数据
        
        Returns:
            DataFrame with columns:
            - 顾问, 考核项目, 目标值, OKR实际完成, 系统实际完成, 差异, 完成率
        """
        rows = []
        
        for okr in self.okr_loader.consultant_okrs:
            # 获取系统实时数据
            sys_stats = self.get_system_stats(okr.consultant_name, year, month)
            
            for indicator in okr.indicators:
                # 判断指标类型并获取对应的系统数据
                sys_value = 0
                target_value = 0
                
                ind_name = indicator.name.lower() if indicator.name else ''
                ind_target = indicator.target.lower() if indicator.target else ''
                
                # 推荐相关指标
                if '推荐' in ind_name or '推荐' in ind_target:
                    sys_value = sys_stats.get('cvsent_count', 0)
                    numbers = re.findall(r'(\d+)', str(indicator.target))
                    if numbers:
                        target_value = int(numbers[0])
                
                # 面试相关指标
                elif '面试' in ind_name or '面试' in ind_target:
                    sys_value = sys_stats.get('interview_count', 0)
                    numbers = re.findall(r'(\d+)', str(indicator.target))
                    if numbers:
                        target_value = int(numbers[0])
                
                # Offer相关指标
                elif 'offer' in ind_name or 'offer' in ind_target:
                    sys_value = sys_stats.get('offer_count', 0)
                    numbers = re.findall(r'(\d+)', str(indicator.target))
                    if numbers:
                        target_value = int(numbers[0])
                
                # 新客户/BD相关
                elif '新' in ind_name or 'bd' in ind_name or 'case' in ind_name:
                    sys_value = sys_stats.get('new_jobs', 0)
                    numbers = re.findall(r'(\d+)', str(indicator.target))
                    if numbers:
                        target_value = int(numbers[0])
                
                # 计算差异
                diff = sys_value - indicator.actual if indicator.actual else sys_value
                
                rows.append({
                    '顾问': okr.consultant_name,
                    '中文名': okr.chinese_name,
                    '考核项目': indicator.name,
                    '考核指标': indicator.target,
                    '权重': indicator.weight,
                    '目标值': target_value,
                    'OKR实际完成': indicator.actual,
                    '系统实际完成': sys_value,
                    '差异': diff,
                    'OKR完成率': indicator.completion_rate,
                    '系统完成率': sys_value / target_value if target_value > 0 else 0,
                })
        
        return pd.DataFrame(rows)


def load_okr_from_file(file_path: str) -> OKRDataLoader:
    """便捷函数：从文件加载OKR数据"""
    loader = OKRDataLoader(file_path)
    loader.parse()
    return loader
