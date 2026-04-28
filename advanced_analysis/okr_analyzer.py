"""
OKR 规则引擎和绩效工资自动计算模块

核心流程：
1. 从Excel模板提取每个顾问的OKR规则（指标、权重、计算规则）
2. 每月自动从系统获取实际业务数据
3. 根据规则自动计算奖金
4. 支持人工校对和调整

支持的OKR指标类型：
- cvsent: 推荐数
- interview: 面试数  
- offer: Offer数
- invoice: 回款金额
- new_job: 新增职位数
- custom: 自定义指标（需手动输入）
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Callable
from dataclasses import dataclass, field
from pathlib import Path
import json
import re
import hashlib


@dataclass
class OKRRule:
    """OKR计算规则"""
    indicator_type: str  # 指标类型: cvsent/interview/offer/invoice/new_job/custom
    indicator_name: str  # 指标名称（显示用）
    target_value: float  # 目标值
    weight: float  # 权重
    bonus_pool: float  # 该指标的奖金池（如1000元 * 权重）
    
    # 计算规则
    threshold_low: float = 0.0  # 低门槛（低于此无奖金）
    threshold_mid: float = 0.0  # 中门槛（达到此发一半）
    threshold_full: float = 0.0  # 全奖门槛（达到此发全额）
    
    # 计分规则（用于周考核类）
    score_per_unit: float = 1.0  # 每单位得分
    score_rule: str = ""  # 详细计分规则描述
    
    # 周期
    period: str = "monthly"  # monthly/weekly/quarterly
    
    @property
    def is_auto_calculable(self) -> bool:
        """是否可从系统自动计算"""
        return self.indicator_type in ['cvsent', 'interview', 'offer', 'invoice', 'new_job']


@dataclass
class ConsultantOKRConfig:
    """顾问OKR配置（从模板提取的规则）"""
    consultant_name: str  # 顾问英文名
    chinese_name: str  # 中文名
    level: str  # 级别
    team: str  # 团队
    manager: str  # 汇报线
    base_bonus: float = 1000.0  # 奖金基数（默认1000）
    
    # OKR规则列表
    rules: List[OKRRule] = field(default_factory=list)
    
    @property
    def total_weight(self) -> float:
        return sum(r.weight for r in self.rules)
    
    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            'consultant_name': self.consultant_name,
            'chinese_name': self.chinese_name,
            'level': self.level,
            'team': self.team,
            'manager': self.manager,
            'base_bonus': self.base_bonus,
            'rules': [
                {
                    'indicator_type': r.indicator_type,
                    'indicator_name': r.indicator_name,
                    'target_value': r.target_value,
                    'weight': r.weight,
                    'bonus_pool': r.bonus_pool,
                    'threshold_low': r.threshold_low,
                    'threshold_mid': r.threshold_mid,
                    'threshold_full': r.threshold_full,
                    'score_per_unit': r.score_per_unit,
                    'score_rule': r.score_rule,
                    'period': r.period,
                }
                for r in self.rules
            ]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ConsultantOKRConfig':
        """从字典反序列化"""
        config = cls(
            consultant_name=data['consultant_name'],
            chinese_name=data.get('chinese_name', ''),
            level=data.get('level', ''),
            team=data.get('team', ''),
            manager=data.get('manager', ''),
            base_bonus=data.get('base_bonus', 1000.0),
        )
        for r_data in data.get('rules', []):
            config.rules.append(OKRRule(**r_data))
        return config


@dataclass
class OKRResult:
    """OKR计算结果（单月）"""
    consultant_name: str
    chinese_name: str
    year: int
    month: int
    
    # 各项指标的实际值和奖金
    indicator_results: List[Dict] = field(default_factory=list)
    
    # 汇总
    total_bonus: float = 0.0
    prev_month_adjustment: float = 0.0  # 上月补发
    final_bonus: float = 0.0  # 最终应发
    
    # 状态
    status: str = "calculated"  # calculated/confirmed/adjusted
    adjusted_by: str = ""  # 调整人
    adjustment_note: str = ""  # 调整说明
    
    def to_dict(self) -> dict:
        return {
            'consultant_name': self.consultant_name,
            'chinese_name': self.chinese_name,
            'year': self.year,
            'month': self.month,
            'indicator_results': self.indicator_results,
            'total_bonus': self.total_bonus,
            'prev_month_adjustment': self.prev_month_adjustment,
            'final_bonus': self.final_bonus,
            'status': self.status,
            'adjusted_by': self.adjusted_by,
            'adjustment_note': self.adjustment_note,
        }


class OKRRuleParser:
    """OKR规则解析器 - 从Excel模板提取计算规则"""
    
    # 指标类型识别关键词
    INDICATOR_PATTERNS = {
        'cvsent': ['推荐', '简历', 'cv', 'cvsent'],
        'interview': ['面试', 'interview', '初面', '一面'],
        'offer': ['offer', '签单', '成单'],
        'invoice': ['回款', '到账', '收款', 'invoice'],
        'new_job': ['新职位', 'new job', 'case in', 'njo', '新增职位'],
        'bd_call': ['bd call', '电话', '拜访', 'f2f'],
        'mapping': ['mapping', '组织架构'],
        'custom': [],  # 其他归为自定义
    }
    
    @classmethod
    def parse_indicator_type(cls, project_name: str, target_desc: str) -> str:
        """根据项目名称和指标描述识别指标类型"""
        text = f"{project_name} {target_desc}".lower()
        
        for ind_type, keywords in cls.INDICATOR_PATTERNS.items():
            if ind_type == 'custom':
                continue
            for kw in keywords:
                if kw in text:
                    return ind_type
        
        return 'custom'
    
    @classmethod
    def parse_target_value(cls, target_desc: str) -> float:
        """从指标描述中解析目标值"""
        if not target_desc or pd.isna(target_desc):
            return 0.0
        
        text = str(target_desc)
        
        # 匹配 "X个/周"、"X个/月"、"X分/周" 等格式
        patterns = [
            r'(\d+)\s*个\s*/\s*(周|月|季度)',
            r'(\d+)\s*分\s*/\s*(周|月)',
            r'(\d+)\s*个\s*(offer|case)',
            r'≥?\s*(\d+)\s*个',
            r'(\d+)\s*%',
            r'(\d+\.?\d*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except:
                    continue
        
        return 0.0
    
    @classmethod
    def parse_score_rule(cls, rule_text: str) -> Dict:
        """解析计分规则文本"""
        result = {
            'score_per_unit': 1.0,
            'threshold_low': 0.0,
            'threshold_mid': 0.0,
            'threshold_full': 0.0,
            'score_rule': rule_text if rule_text else '',
        }
        
        if not rule_text or pd.isna(rule_text):
            return result
        
        text = str(rule_text)
        
        # 解析 "①推荐报告1分，第一轮面试1分，offer 3分"
        score_patterns = [
            r'(\w+)\s*(\d+)\s*分',
            r'(\w+)\s*(\d+)\s*分',
        ]
        
        # 解析 "0-6分无奖金，7-9分一半，10分及10分以上全额"
        threshold_patterns = [
            r'(\d+)\s*-\s*(\d+)\s*分?\s*无?半?全?额?',
            r'(\d+)\s*分?\s*及?以?上?\s*全?额?',
        ]
        
        # 尝试提取阈值
        low_match = re.search(r'(\d+)\s*-\s*(\d+)\s*分?\s*无', text)
        if low_match:
            result['threshold_low'] = float(low_match.group(2))
        
        mid_match = re.search(r'(\d+)\s*-\s*(\d+)\s*分?\s*一半|半额', text)
        if mid_match:
            result['threshold_mid'] = float(mid_match.group(1))
        
        full_match = re.search(r'(\d+)\s*分?\s*及?以?上?\s*全?额?', text)
        if full_match:
            result['threshold_full'] = float(full_match.group(1))
        
        return result
    
    @classmethod
    def parse_period(cls, target_desc: str, project_name: str) -> str:
        """解析考核周期"""
        text = f"{project_name} {target_desc}".lower()
        
        if '/周' in text or '周' in text:
            return 'weekly'
        elif '/月' in text or '月' in text:
            return 'monthly'
        elif '季度' in text or 'quarter' in text:
            return 'quarterly'
        
        return 'monthly'


class OKRConfigManager:
    """OKR配置管理器 - 保存和加载OKR规则配置"""
    
    CONFIG_DIR = Path(__file__).parent / "okr_configs"
    
    def __init__(self):
        self.CONFIG_DIR.mkdir(exist_ok=True)
    
    def _get_config_path(self, consultant_name: str) -> Path:
        """获取配置文件路径"""
        safe_name = re.sub(r'[^\w\-]', '_', consultant_name)
        return self.CONFIG_DIR / f"{safe_name}.json"
    
    def save_config(self, config: ConsultantOKRConfig):
        """保存顾问OKR配置"""
        path = self._get_config_path(config.consultant_name)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
    
    def load_config(self, consultant_name: str) -> Optional[ConsultantOKRConfig]:
        """加载顾问OKR配置"""
        path = self._get_config_path(consultant_name)
        if not path.exists():
            return None
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return ConsultantOKRConfig.from_dict(data)
    
    def load_all_configs(self) -> List[ConsultantOKRConfig]:
        """加载所有顾问的OKR配置"""
        configs = []
        for path in self.CONFIG_DIR.glob("*.json"):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            configs.append(ConsultantOKRConfig.from_dict(data))
        return configs
    
    def delete_config(self, consultant_name: str):
        """删除顾问OKR配置"""
        path = self._get_config_path(consultant_name)
        if path.exists():
            path.unlink()
    
    def parse_from_excel(self, file_path: str) -> List[ConsultantOKRConfig]:
        """从Excel模板解析OKR规则配置"""
        df = pd.read_excel(file_path, header=None)
        
        # 找出所有顾问行
        name_rows = []
        for i in range(len(df)):
            val = df.iloc[i, 1]
            if (pd.notna(val) and 
                val != '英文名字' and 
                isinstance(val, str) and 
                len(val) > 1 and 
                val not in ['NaN', 'nan']):
                name_rows.append(i)
        
        configs = []
        
        for i, idx in enumerate(name_rows):
            next_idx = name_rows[i+1] if i+1 < len(name_rows) else len(df)
            config = self._parse_consultant_config(df, idx, next_idx)
            if config:
                configs.append(config)
                # 自动保存
                self.save_config(config)
        
        return configs
    
    def _parse_consultant_config(self, df: pd.DataFrame, start_row: int, end_row: int) -> Optional[ConsultantOKRConfig]:
        """解析单个顾问的OKR配置"""
        en_name = df.iloc[start_row, 1]
        cn_name = df.iloc[start_row, 2]
        
        if pd.isna(en_name) or en_name == '英文名字':
            return None
        
        config = ConsultantOKRConfig(
            consultant_name=str(en_name).strip(),
            chinese_name=str(cn_name).strip() if pd.notna(cn_name) else '',
            level=str(df.iloc[start_row, 3]).strip() if pd.notna(df.iloc[start_row, 3]) else '',
            team=str(df.iloc[start_row, 4]).strip() if pd.notna(df.iloc[start_row, 4]) else '',
            manager=str(df.iloc[start_row, 5]).strip() if pd.notna(df.iloc[start_row, 5]) else '',
        )
        
        # 解析OKR规则
        for row_idx in range(start_row, end_row):
            weight = self._parse_number(df.iloc[row_idx, 10])
            if pd.isna(weight) or weight == 0:
                continue
            
            project = df.iloc[row_idx, 8]
            target = df.iloc[row_idx, 9]
            rule_text = df.iloc[row_idx, 11]
            
            # 如果子行没有项目名称，使用主行的
            if pd.isna(project) and row_idx > start_row:
                project = df.iloc[start_row, 8]
            
            # 解析指标类型
            ind_type = OKRRuleParser.parse_indicator_type(
                str(project) if pd.notna(project) else '',
                str(target) if pd.notna(target) else ''
            )
            
            # 解析目标值
            target_value = OKRRuleParser.parse_target_value(str(target) if pd.notna(target) else '')
            
            # 解析计分规则
            score_info = OKRRuleParser.parse_score_rule(str(rule_text) if pd.notna(rule_text) else '')
            
            # 解析周期
            period = OKRRuleParser.parse_period(
                str(target) if pd.notna(target) else '',
                str(project) if pd.notna(project) else ''
            )
            
            # 计算奖金池
            bonus_pool = config.base_bonus * weight
            
            rule = OKRRule(
                indicator_type=ind_type,
                indicator_name=str(project).strip() if pd.notna(project) else str(target).strip() if pd.notna(target) else '',
                target_value=target_value,
                weight=weight,
                bonus_pool=bonus_pool,
                threshold_low=score_info['threshold_low'],
                threshold_mid=score_info['threshold_mid'],
                threshold_full=score_info['threshold_full'],
                score_per_unit=score_info['score_per_unit'],
                score_rule=score_info['score_rule'],
                period=period,
            )
            
            config.rules.append(rule)
        
        return config
    
    @staticmethod
    def _parse_number(val) -> float:
        if pd.isna(val):
            return 0.0
        try:
            return float(val)
        except:
            return 0.0


class OKRCalculator:
    """OKR奖金计算器 - 根据规则+实际数据计算奖金"""
    
    def __init__(self, db_client=None):
        self.db_client = db_client
    
    def set_db_client(self, db_client):
        self.db_client = db_client
    
    def get_system_data(self, consultant_name: str, year: int, month: int) -> Dict[str, float]:
        """
        从数据库获取顾问的月度业务数据
        
        Returns:
            {
                'cvsent_count': 推荐数,
                'interview_count': 面试数,
                'offer_count': Offer数,
                'offer_amount': Offer金额,
                'invoice_amount': 回款金额,
                'new_job_count': 新增职位数,
            }
        """
        if not self.db_client:
            return {}
        
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year+1}-01-01"
        else:
            end_date = f"{year}-{month+1:02d}-01"
        
        # 获取顾问ID
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
        stats['new_job_count'] = int(job_df.iloc[0]['cnt']) if not job_df.empty else 0
        
        return stats
    
    def calculate_indicator_bonus(self, rule: OKRRule, actual_value: float) -> Dict:
        """
        计算单个指标的奖金
        
        Returns:
            {
                'actual_value': 实际值,
                'target_value': 目标值,
                'completion_rate': 完成率,
                'bonus': 计算奖金,
                'calculation_detail': 计算说明,
            }
        """
        result = {
            'actual_value': actual_value,
            'target_value': rule.target_value,
            'completion_rate': 0.0,
            'bonus': 0.0,
            'calculation_detail': '',
        }
        
        if rule.target_value <= 0:
            result['calculation_detail'] = '目标值未设置，无法计算'
            return result
        
        # 计算完成率
        completion = actual_value / rule.target_value
        result['completion_rate'] = completion
        
        # 根据规则计算奖金
        if rule.threshold_full > 0:
            # 有阈值规则（如周考核类）
            if actual_value >= rule.threshold_full:
                result['bonus'] = rule.bonus_pool
                result['calculation_detail'] = f'达到全额门槛({rule.threshold_full})，发放全额奖金 {rule.bonus_pool}元'
            elif rule.threshold_mid > 0 and actual_value >= rule.threshold_mid:
                result['bonus'] = rule.bonus_pool * 0.5
                result['calculation_detail'] = f'达到半额门槛({rule.threshold_mid})，发放一半奖金 {result["bonus"]}元'
            else:
                result['bonus'] = 0
                result['calculation_detail'] = f'未达到最低门槛({rule.threshold_low or 0})，无奖金'
        else:
            # 按比例计算
            if completion >= 1.0:
                result['bonus'] = rule.bonus_pool
                result['calculation_detail'] = f'完成率{completion*100:.1f}%，达到目标，发放全额奖金 {rule.bonus_pool}元'
            elif completion >= 0.7:
                result['bonus'] = rule.bonus_pool * 0.5
                result['calculation_detail'] = f'完成率{completion*100:.1f}%，达到70%，发放一半奖金 {result["bonus"]}元'
            else:
                result['bonus'] = 0
                result['calculation_detail'] = f'完成率{completion*100:.1f}%，未达到70%，无奖金'
        
        return result
    
    def calculate_monthly_bonus(self, config: ConsultantOKRConfig, year: int, month: int) -> OKRResult:
        """
        计算顾问月度奖金
        
        Args:
            config: 顾问OKR配置
            year: 年份
            month: 月份
        
        Returns:
            OKRResult
        """
        result = OKRResult(
            consultant_name=config.consultant_name,
            chinese_name=config.chinese_name,
            year=year,
            month=month,
        )
        
        # 获取系统数据
        system_data = self.get_system_data(config.consultant_name, year, month)
        
        total_bonus = 0.0
        
        for rule in config.rules:
            # 获取实际值
            actual_value = 0.0
            if rule.indicator_type == 'cvsent':
                actual_value = system_data.get('cvsent_count', 0)
            elif rule.indicator_type == 'interview':
                actual_value = system_data.get('interview_count', 0)
            elif rule.indicator_type == 'offer':
                actual_value = system_data.get('offer_count', 0)
            elif rule.indicator_type == 'invoice':
                actual_value = system_data.get('invoice_amount', 0)
            elif rule.indicator_type == 'new_job':
                actual_value = system_data.get('new_job_count', 0)
            else:
                # 自定义指标，需要手动输入
                actual_value = 0.0
            
            # 计算奖金
            calc_result = self.calculate_indicator_bonus(rule, actual_value)
            
            result.indicator_results.append({
                'indicator_type': rule.indicator_type,
                'indicator_name': rule.indicator_name,
                'weight': rule.weight,
                'target_value': rule.target_value,
                'actual_value': actual_value,
                'completion_rate': calc_result['completion_rate'],
                'bonus_pool': rule.bonus_pool,
                'calculated_bonus': calc_result['bonus'],
                'calculation_detail': calc_result['calculation_detail'],
                'is_auto': rule.is_auto_calculable,
            })
            
            total_bonus += calc_result['bonus']
        
        result.total_bonus = total_bonus
        result.final_bonus = total_bonus + result.prev_month_adjustment
        
        return result
    
    def calculate_all(self, configs: List[ConsultantOKRConfig], year: int, month: int) -> List[OKRResult]:
        """计算所有顾问的月度奖金"""
        results = []
        for config in configs:
            result = self.calculate_monthly_bonus(config, year, month)
            results.append(result)
        return results


class OKRResultStore:
    """OKR计算结果存储 - 支持保存和加载历史计算结果"""
    
    RESULT_DIR = Path(__file__).parent / "okr_results"
    
    def __init__(self):
        self.RESULT_DIR.mkdir(exist_ok=True)
    
    def _get_result_path(self, consultant_name: str, year: int, month: int) -> Path:
        safe_name = re.sub(r'[^\w\-]', '_', consultant_name)
        return self.RESULT_DIR / f"{safe_name}_{year}{month:02d}.json"
    
    def save_result(self, result: OKRResult):
        """保存计算结果"""
        path = self._get_result_path(result.consultant_name, result.year, result.month)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
    
    def load_result(self, consultant_name: str, year: int, month: int) -> Optional[OKRResult]:
        """加载计算结果"""
        path = self._get_result_path(consultant_name, year, month)
        if not path.exists():
            return None
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return OKRResult(**{k: v for k, v in data.items() if k in OKRResult.__dataclass_fields__})
    
    def load_month_results(self, year: int, month: int) -> List[OKRResult]:
        """加载某月的所有计算结果"""
        results = []
        pattern = f"*_{year}{month:02d}.json"
        for path in self.RESULT_DIR.glob(pattern):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            results.append(OKRResult(**{k: v for k, v in data.items() if k in OKRResult.__dataclass_fields__}))
        return results
    
    def confirm_result(self, consultant_name: str, year: int, month: int, adjusted_by: str = "", note: str = ""):
        """确认计算结果"""
        result = self.load_result(consultant_name, year, month)
        if result:
            result.status = "confirmed"
            result.adjusted_by = adjusted_by
            result.adjustment_note = note
            self.save_result(result)
    
    def adjust_bonus(self, consultant_name: str, year: int, month: int, new_bonus: float, adjusted_by: str, note: str):
        """调整奖金"""
        result = self.load_result(consultant_name, year, month)
        if result:
            result.final_bonus = new_bonus
            result.status = "adjusted"
            result.adjusted_by = adjusted_by
            result.adjustment_note = note
            self.save_result(result)


# 便捷函数
def parse_okr_rules_from_excel(file_path: str) -> List[ConsultantOKRConfig]:
    """从Excel解析OKR规则配置"""
    manager = OKRConfigManager()
    return manager.parse_from_excel(file_path)


def calculate_monthly_okr_bonus(year: int, month: int, db_client=None) -> List[OKRResult]:
    """计算月度OKR奖金"""
    config_manager = OKRConfigManager()
    configs = config_manager.load_all_configs()
    
    calculator = OKRCalculator(db_client)
    results = calculator.calculate_all(configs, year, month)
    
    # 保存结果
    result_store = OKRResultStore()
    for result in results:
        result_store.save_result(result)
    
    return results
