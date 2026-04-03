"""
猎头公司财务分析工具 - 数据模型和核心计算逻辑
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import json


@dataclass
class Deal:
    """成单记录"""
    deal_id: str
    client_name: str
    candidate_name: str
    position: str
    consultant: str
    deal_date: datetime
    annual_salary: float  # 候选人年薪
    fee_rate: float  # 费率（百分比，如20表示20%）
    fee_amount: float  # 佣金金额
    payment_date: Optional[datetime] = None  # 回款日期
    payment_status: str = "未回款"  # 未回款/部分回款/已回款
    actual_payment: float = 0  # 实际回款金额
    # 上一年遗留回款（算入本年收入）
    prior_year_collection: float = 0  # 上一年遗留回款金额
    
    @property
    def gross_profit(self) -> float:
        """毛利润 = 佣金金额 - 顾问提成（假设提成30%）"""
        consultant_bonus = self.fee_amount * 0.30
        return self.fee_amount - consultant_bonus
    
    @property
    def total_current_year_income(self) -> float:
        """本年收入 = 实际回款 + 上一年遗留回款"""
        return self.actual_payment + self.prior_year_collection


@dataclass
class Forecast:
    """在途单/预测收入"""
    forecast_id: str  # 预测单编号
    client_name: str  # 客户名称
    position: str  # 职位名称
    consultant: str  # 负责顾问
    candidate_name: str = ""  # 候选人姓名（可选）
    # 预计佣金
    estimated_salary: float = 0  # 预计年薪
    fee_rate: float = 20  # 费率(%)
    estimated_fee: float = 0  # 预计佣金（如果已知）
    # 成功率预测
    success_rate: float = 0  # 成功率(%)，如80表示80%
    # 阶段
    stage: str = "初期接触"  # 阶段：初期接触/推荐简历/面试中/offer谈判/待发offer
    # 日期
    start_date: datetime = None  # 开始日期
    expected_close_date: datetime = None  # 预计成交日期
    create_date: datetime = None  # 创建日期
    note: str = ""  # 备注
    
    @property
    def weighted_revenue(self) -> float:
        """加权预测收入 = 预计佣金 × 成功率"""
        fee = self.estimated_fee if self.estimated_fee > 0 else (self.estimated_salary * self.fee_rate / 100)
        return fee * (self.success_rate / 100)
    
    @property
    def estimated_profit(self) -> float:
        """预计利润（假设成本为佣金的60%）"""
        return self.weighted_revenue * 0.4


@dataclass
class Consultant:
    """顾问信息"""
    name: str
    base_salary: float  # 底薪（用于真实成本计算）
    join_date: datetime
    team: str = ""
    is_active: bool = True
    
    # 绩效指标
    monthly_kpi: float = 50000  # 月度业绩目标
    
    # 内部核算用基本月薪（给顾问展示的盈亏分析用）
    # 如果为0，则使用 base_salary
    internal_base_salary: float = 0  # 内部核算基本月薪
    

@dataclass
class Expense:
    """费用支出"""
    expense_id: str
    category: str  # 人员工资/租金/差旅/招待/律师费/财务费/猎头系统费用/其他
    amount: float
    date: datetime
    department: str = ""  # 部门
    note: str = ""  # 备注
    

class RecruitmentFinanceAnalyzer:
    """猎头公司财务分析器"""
    
    def __init__(self):
        self.deals: List[Deal] = []
        self.consultants: List[Consultant] = []
        self.expenses: List[Expense] = []
        self.forecasts: List[Forecast] = []  # 在途单/预测收入
        
    def add_deal(self, deal: Deal):
        """添加成单记录"""
        self.deals.append(deal)
        
    def add_consultant(self, consultant: Consultant):
        """添加顾问"""
        self.consultants.append(consultant)
        
    def add_expense(self, expense: Expense):
        """添加费用"""
        self.expenses.append(expense)
        
    def add_forecast(self, forecast: Forecast):
        """添加预测/在途单"""
        self.forecasts.append(forecast)
        
    def load_from_dataframes(self, deals_df: pd.DataFrame, 
                            consultants_df: pd.DataFrame = None,
                            expenses_df: pd.DataFrame = None):
        """从DataFrame加载数据"""
        # 清空现有数据
        self.deals = []
        self.consultants = []
        self.expenses = []
        
        # 加载成单数据
        for idx, row in deals_df.iterrows():
            try:
                # 处理关键字段 - 支持中英文列名
                # 佣金金额 - 尝试多个可能的列名
                fee_amount = 0.0
                for col in ['fee_amount', '佣金', 'fee', '佣金金额']:
                    if col in row and pd.notna(row[col]):
                        val = pd.to_numeric(row[col], errors='coerce')
                        if pd.notna(val):
                            fee_amount = float(val)
                            break
                
                # 实际回款
                actual_payment = 0.0
                for col in ['actual_payment', '实际回款', '回款', 'actual']:
                    if col in row and pd.notna(row[col]):
                        val = pd.to_numeric(row[col], errors='coerce')
                        if pd.notna(val):
                            actual_payment = float(val)
                            break
                
                # 上年遗留回款
                prior_year = 0.0
                for col in ['prior_year_collection', '上年遗留回款', '遗留回款', 'prior_collection']:
                    if col in row and pd.notna(row[col]):
                        val = pd.to_numeric(row[col], errors='coerce')
                        if pd.notna(val):
                            prior_year = float(val)
                            break
                
                # 年薪（可选）
                annual_salary = 0.0
                for col in ['annual_salary', '年薪']:
                    if col in row and pd.notna(row[col]):
                        val = pd.to_numeric(row[col], errors='coerce')
                        if pd.notna(val):
                            annual_salary = float(val)
                            break
                
                # 费率（可选）
                fee_rate = 20.0
                for col in ['fee_rate', '费率']:
                    if col in row and pd.notna(row[col]):
                        val = pd.to_numeric(row[col], errors='coerce')
                        if pd.notna(val):
                            fee_rate = float(val)
                            break
                
                # 字符串字段
                deal_id = ''
                for col in ['deal_id', '成单编号', '编号']:
                    if col in row and pd.notna(row[col]):
                        deal_id = str(row[col]).strip()
                        break
                
                client_name = ''
                for col in ['client_name', '客户', '客户名称']:
                    if col in row and pd.notna(row[col]):
                        client_name = str(row[col]).strip()
                        break
                
                candidate_name = ''
                for col in ['candidate_name', '候选人', '姓名']:
                    if col in row and pd.notna(row[col]):
                        candidate_name = str(row[col]).strip()
                        break
                
                position = ''
                for col in ['position', '职位']:
                    if col in row and pd.notna(row[col]):
                        position = str(row[col]).strip()
                        break
                
                consultant = ''
                for col in ['consultant', '顾问', '负责顾问']:
                    if col in row and pd.notna(row[col]):
                        consultant = str(row[col]).strip()
                        break
                
                payment_status = '未回款'
                for col in ['payment_status', '回款状态']:
                    if col in row and pd.notna(row[col]):
                        payment_status = str(row[col]).strip()
                        break
                
                # 日期处理
                deal_date = datetime.now()
                for col in ['deal_date', '成单日期', '日期']:
                    if col in row and pd.notna(row[col]):
                        try:
                            deal_date = pd.to_datetime(row[col])
                            break
                        except:
                            continue
                
                payment_date = None
                for col in ['payment_date', '回款日期']:
                    if col in row and pd.notna(row[col]):
                        try:
                            payment_date = pd.to_datetime(row[col])
                            break
                        except:
                            continue
                
                deal = Deal(
                    deal_id=deal_id,
                    client_name=client_name,
                    candidate_name=candidate_name,
                    position=position,
                    consultant=consultant,
                    deal_date=deal_date,
                    annual_salary=annual_salary,
                    fee_rate=fee_rate,
                    fee_amount=fee_amount,
                    payment_date=payment_date,
                    payment_status=payment_status,
                    actual_payment=actual_payment,
                    prior_year_collection=prior_year
                )
                self.add_deal(deal)
            except Exception as e:
                print(f"处理第 {idx} 行数据时出错: {e}")
                continue
            
        # 加载顾问数据
        if consultants_df is not None:
            for idx, row in consultants_df.iterrows():
                try:
                    # 姓名
                    name = ''
                    for col in ['name', '姓名', '顾问姓名']:
                        if col in row and pd.notna(row[col]):
                            name = str(row[col]).strip()
                            break
                    
                    # 底薪
                    base_salary = 0.0
                    for col in ['base_salary', '底薪', '基本月薪']:
                        if col in row and pd.notna(row[col]):
                            val = pd.to_numeric(row[col], errors='coerce')
                            if pd.notna(val):
                                base_salary = float(val)
                                break
                    
                    # 内部核算基本月薪
                    internal_salary = 0.0
                    for col in ['internal_base_salary', '内部核算月薪']:
                        if col in row and pd.notna(row[col]):
                            val = pd.to_numeric(row[col], errors='coerce')
                            if pd.notna(val):
                                internal_salary = float(val)
                                break
                    if internal_salary == 0:
                        internal_salary = base_salary
                    
                    # 团队
                    team = ''
                    for col in ['team', '团队', '部门']:
                        if col in row and pd.notna(row[col]):
                            team = str(row[col]).strip()
                            break
                    
                    # 月度KPI
                    monthly_kpi = 50000.0
                    for col in ['monthly_kpi', '月度KPI', 'KPI']:
                        if col in row and pd.notna(row[col]):
                            val = pd.to_numeric(row[col], errors='coerce')
                            if pd.notna(val):
                                monthly_kpi = float(val)
                                break
                    
                    # 入职日期
                    join_date = datetime.now()
                    for col in ['join_date', '入职日期']:
                        if col in row and pd.notna(row[col]):
                            try:
                                join_date = pd.to_datetime(row[col])
                                break
                            except:
                                continue
                    
                    # 是否在职
                    is_active = True
                    for col in ['is_active', '在职']:
                        if col in row and pd.notna(row[col]):
                            val = str(row[col]).lower()
                            is_active = val in ['true', '1', 'yes', '是', '在职']
                            break
                    
                    consultant = Consultant(
                        name=name,
                        base_salary=base_salary,
                        join_date=join_date,
                        team=team,
                        is_active=is_active,
                        monthly_kpi=monthly_kpi,
                        internal_base_salary=internal_salary
                    )
                    self.add_consultant(consultant)
                except Exception as e:
                    print(f"处理顾问第 {idx} 行数据时出错: {e}")
                    continue
                
        # 加载费用数据
        if expenses_df is not None:
            for idx, row in expenses_df.iterrows():
                try:
                    # 费用类型
                    category = '其他'
                    for col in ['category', '费用类型']:
                        if col in row and pd.notna(row[col]):
                            category = str(row[col]).strip()
                            break
                    
                    # 部门
                    department = ''
                    for col in ['department', '部门']:
                        if col in row and pd.notna(row[col]):
                            department = str(row[col]).strip()
                            break
                    
                    # 备注
                    note = ''
                    for col in ['note', '备注', 'description', '说明']:
                        if col in row and pd.notna(row[col]):
                            note = str(row[col]).strip()
                            break
                    
                    # 金额
                    amount = 0.0
                    for col in ['amount', '金额']:
                        if col in row and pd.notna(row[col]):
                            val = pd.to_numeric(row[col], errors='coerce')
                            if pd.notna(val):
                                amount = float(val)
                                break
                    
                    # 日期
                    date = datetime.now()
                    for col in ['date', '日期']:
                        if col in row and pd.notna(row[col]):
                            try:
                                date = pd.to_datetime(row[col])
                                break
                            except:
                                continue
                    
                    # 费用编号
                    expense_id = f'E{idx+1:04d}'
                    for col in ['expense_id', '费用编号']:
                        if col in row and pd.notna(row[col]):
                            expense_id = str(row[col]).strip()
                            break
                    
                    expense = Expense(
                        expense_id=expense_id,
                        category=category,
                        amount=amount,
                        date=date,
                        department=department,
                        note=note
                    )
                    self.add_expense(expense)
                except Exception as e:
                    print(f"处理费用第 {idx} 行数据时出错: {e}")
                    continue
    
    def load_forecasts_from_dataframe(self, forecast_df: pd.DataFrame):
        """从DataFrame加载预测/在途单数据
        支持forecastassignment表的字段映射
        """
        if forecast_df is None or forecast_df.empty:
            return
            
        for idx, row in forecast_df.iterrows():
            try:
                # 预测单编号
                forecast_id = f'F{idx+1:04d}'
                for col in ['forecast_id', '预测编号', '编号', 'id']:
                    if col in row and pd.notna(row[col]):
                        forecast_id = str(row[col]).strip()
                        break
                
                # 客户名称 (支持forecastassignment的'客户')
                client_name = ''
                for col in ['client_name', '客户', '客户名称']:
                    if col in row and pd.notna(row[col]):
                        client_name = str(row[col]).strip()
                        break
                
                # 职位 (支持forecastassignment的'项目')
                position = ''
                for col in ['position', '职位', '岗位', '项目']:
                    if col in row and pd.notna(row[col]):
                        position = str(row[col]).strip()
                        break
                
                # 顾问 (支持forecastassignment的'用户')
                consultant = ''
                for col in ['consultant', '顾问', '负责顾问', '用户']:
                    if col in row and pd.notna(row[col]):
                        consultant = str(row[col]).strip()
                        break
                
                # 候选人（可选）
                candidate_name = ''
                for col in ['candidate_name', '候选人', '姓名']:
                    if col in row and pd.notna(row[col]):
                        candidate_name = str(row[col]).strip()
                        break
                
                # 预计年薪 (支持forecastassignment的'收费基数')
                estimated_salary = 0.0
                for col in ['estimated_salary', '预计年薪', '年薪', '收费基数']:
                    if col in row and pd.notna(row[col]):
                        val = pd.to_numeric(row[col], errors='coerce')
                        if pd.notna(val):
                            estimated_salary = float(val)
                            break
                
                # 费率 (支持forecastassignment的'费率'，注意是小数0.21格式)
                fee_rate = 20.0
                for col in ['fee_rate', '费率']:
                    if col in row and pd.notna(row[col]):
                        val = pd.to_numeric(row[col], errors='coerce')
                        if pd.notna(val):
                            fee_rate = float(val)
                            # 如果费率是小数形式(如0.21)，转换为百分比(21)
                            if fee_rate < 1:
                                fee_rate = fee_rate * 100
                            break
                
                # 预计佣金（如果直接提供，支持forecastassignment的'Forecast * 成功率'）
                estimated_fee = 0.0
                for col in ['estimated_fee', '预计佣金', '佣金', 'Forecast * 成功率', 'Forecast分配']:
                    if col in row and pd.notna(row[col]):
                        val = pd.to_numeric(row[col], errors='coerce')
                        if pd.notna(val):
                            estimated_fee = float(val)
                            break
                
                # 成功率 (支持forecastassignment的'比例')
                success_rate = 0.0
                for col in ['success_rate', '成功率', '成功概率', '比例']:
                    if col in row and pd.notna(row[col]):
                        val = pd.to_numeric(row[col], errors='coerce')
                        if pd.notna(val):
                            success_rate = float(val)
                            # 如果比例是大于1的数字(如10.0)，认为是百分比形式
                            # 如果比例是小数(如0.1)，转换为百分比(10)
                            if success_rate < 1:
                                success_rate = success_rate * 100
                            break
                
                # 阶段 (支持forecastassignment的'最新进展')
                stage = '初期接触'
                for col in ['stage', '阶段', '状态', '最新进展']:
                    if col in row and pd.notna(row[col]):
                        stage = str(row[col]).strip()
                        break
                
                # 开始日期
                start_date = None
                for col in ['start_date', '开始日期']:
                    if col in row and pd.notna(row[col]):
                        try:
                            start_date = pd.to_datetime(row[col])
                            break
                        except:
                            continue
                
                # 预计成交日期 (支持forecastassignment的'预计成功时间')
                expected_close_date = None
                for col in ['expected_close_date', '预计成交日期', '预计日期', '预计成功时间']:
                    if col in row and pd.notna(row[col]):
                        try:
                            expected_close_date = pd.to_datetime(row[col])
                            break
                        except:
                            continue
                
                # 备注 (支持forecastassignment的'Forecast备注')
                note = ''
                for col in ['note', '备注', '说明', 'Forecast备注']:
                    if col in row and pd.notna(row[col]):
                        note = str(row[col]).strip()
                        break
                
                forecast = Forecast(
                    forecast_id=forecast_id,
                    client_name=client_name,
                    position=position,
                    consultant=consultant,
                    candidate_name=candidate_name,
                    estimated_salary=estimated_salary,
                    fee_rate=fee_rate,
                    estimated_fee=estimated_fee,
                    success_rate=success_rate,
                    stage=stage,
                    start_date=start_date,
                    expected_close_date=expected_close_date,
                    create_date=datetime.now(),
                    note=note
                )
                self.add_forecast(forecast)
            except Exception as e:
                print(f"处理预测第 {idx} 行数据时出错: {e}")
                continue
    
    # ============ 收入分析 ============
    
    def get_revenue_summary(self, start_date: datetime = None, 
                           end_date: datetime = None) -> Dict:
        """收入汇总分析
        注意：actual_payment 已包含所有回款（本年+上年），prior_year_collection 只是明细标注
        """
        deals = self._filter_deals_by_date(start_date, end_date)
        
        if not deals:
            return {
                'total_deals': 0,
                'total_fee': 0,
                'total_collected': 0,
                'prior_year_collection': 0,
                'current_year_collection': 0,  # 本年成立单的回款
                'collection_rate': 0,
                'avg_deal_size': 0,
                'avg_annual_salary': 0
            }
        
        total_fee = sum(d.fee_amount or 0 for d in deals)
        total_collected = sum(d.actual_payment or 0 for d in deals)  # 已包含上年遗留
        # 上年遗留回款（仅用于明细展示）
        prior_year_collection = sum(d.prior_year_collection or 0 for d in deals)
        # 本年成立单的回款 = 总回款 - 上年遗留回款
        current_year_collection = total_collected - prior_year_collection
        
        collection_rate = total_collected / total_fee * 100 if total_fee > 0 else 0
        
        # 计算平均年薪（只统计有年薪数据的成单）
        salaries = [(d.annual_salary or 0) for d in deals if (d.annual_salary or 0) > 0]
        avg_salary = sum(salaries) / len(salaries) if salaries else 0
        
        return {
            'total_deals': len(deals),
            'total_fee': total_fee,
            'total_collected': total_collected,  # 总回款（含上年遗留）
            'prior_year_collection': prior_year_collection,  # 其中：上年遗留
            'current_year_collection': current_year_collection,  # 其中：本年回款
            'collection_rate': collection_rate,
            'avg_deal_size': total_fee / len(deals),
            'avg_annual_salary': avg_salary
        }
    
    def get_monthly_revenue(self) -> pd.DataFrame:
        """月度收入趋势
        注意：actual_payment 已包含所有回款，prior_year_collection 只是明细
        """
        if not self.deals:
            return pd.DataFrame(columns=['月份', '成单数', '佣金金额', '回款金额', '上年遗留回款', '本年回款'])
            
        df = pd.DataFrame([{
            '月份': d.deal_date.strftime('%Y-%m') if d.deal_date else '',
            '佣金金额': d.fee_amount or 0,
            '回款金额': d.actual_payment or 0,  # 总回款（含上年遗留）
            '上年遗留回款': d.prior_year_collection or 0,
            '本年回款': (d.actual_payment or 0) - (d.prior_year_collection or 0)  # 本年成立单的回款
        } for d in self.deals])
        
        monthly = df.groupby('月份').agg({
            '佣金金额': 'sum',
            '回款金额': 'sum',
            '上年遗留回款': 'sum',
            '本年回款': 'sum'
        }).reset_index()
        monthly['成单数'] = df.groupby('月份').size().values
        
        return monthly.sort_values('月份')
    
    def get_revenue_by_consultant(self) -> pd.DataFrame:
        """顾问业绩排名"""
        if not self.deals:
            return pd.DataFrame(columns=['顾问', '成单数', '佣金总额', '回款总额', '平均单值'])
            
        df = pd.DataFrame([{
            '顾问': d.consultant or '未知',
            '佣金金额': d.fee_amount or 0,
            '回款金额': d.actual_payment or 0
        } for d in self.deals])
        
        summary = df.groupby('顾问').agg({
            '佣金金额': ['sum', 'count', 'mean'],
            '回款金额': 'sum'
        }).reset_index()
        
        summary.columns = ['顾问', '佣金总额', '成单数', '平均单值', '回款总额']
        summary = summary.sort_values('佣金总额', ascending=False)
        
        return summary
    
    def get_revenue_by_client(self) -> pd.DataFrame:
        """客户收入分析"""
        if not self.deals:
            return pd.DataFrame(columns=['客户', '成单数', '佣金总额', '平均职位年薪'])
            
        df = pd.DataFrame([{
            '客户': d.client_name or '未知',
            '佣金金额': d.fee_amount or 0,
            '年薪': d.annual_salary if (d.annual_salary or 0) > 0 else None
        } for d in self.deals])
        
        summary = df.groupby('客户').agg({
            '佣金金额': ['sum', 'count'],
            '年薪': 'mean'
        }).reset_index()
        
        summary.columns = ['客户', '佣金总额', '成单数', '平均职位年薪']
        summary = summary.sort_values('佣金总额', ascending=False)
        
        return summary
    
    # ============ 成本分析 ============
    
    def get_expense_summary(self, start_date: datetime = None, 
                           end_date: datetime = None) -> Dict:
        """费用汇总"""
        expenses = self._filter_expenses_by_date(start_date, end_date)
        
        # 计算人力成本
        consultant_costs = self._calculate_consultant_costs(start_date, end_date)
        
        total_expense = sum(e.amount for e in expenses) + consultant_costs
        
        return {
            'total_expense': total_expense,
            'operational_expense': sum(e.amount for e in expenses),
            'personnel_cost': consultant_costs,
            'by_category': self._get_expense_by_category(expenses, consultant_costs)
        }
    
    def get_internal_expense_summary(self, start_date: datetime = None,
                                     end_date: datetime = None) -> Dict:
        """
        内部核算版本：费用汇总（给顾问展示的盈亏分析）
        不包含真实运营费用，只使用内部核算的顾问成本
        """
        # 计算内部核算顾问成本
        internal_costs = self._calculate_internal_consultant_costs(start_date, end_date)
        
        return {
            'total_expense': internal_costs['total_cost'],
            'consultant_cost': internal_costs['total_cost'],
            'consultant_details': internal_costs['consultant_details'],
            'months': internal_costs['months'],
            'is_internal': True
        }
    
    def _calculate_consultant_costs(self, start_date: datetime = None,
                                    end_date: datetime = None) -> float:
        """计算顾问人力成本（底薪+提成）"""
        if not start_date or not end_date:
            # 使用默认时间范围（最近3个月）
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
        
        months = max(1, (end_date - start_date).days / 30)
        
        # 底薪
        base_salary_total = sum((c.base_salary or 0) for c in self.consultants if c.is_active) * months
        
        # 提成（已成交单的30%）
        deals = self._filter_deals_by_date(start_date, end_date)
        bonus_total = sum((d.fee_amount or 0) * 0.30 for d in deals)
        
        return base_salary_total + bonus_total
    
    def _calculate_internal_consultant_costs(self, start_date: datetime = None,
                                              end_date: datetime = None) -> Dict:
        """
        内部核算版本：顾问成本计算
        公式：顾问基本月薪 × 3 × 1.2（20%利润目标）
        3倍包括：工资、社保公积金、顾问奖金、增值税、营运成本（支持部门、房租、办公等）
        """
        if not start_date or not end_date:
            # 使用默认时间范围（最近3个月）
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
        
        months = max(1, (end_date - start_date).days / 30)
        
        # 计算每个顾问的内部成本
        consultant_internal_costs = []
        total_internal_cost = 0
        
        for c in self.consultants:
            if c.is_active:
                # 使用内部核算基本月薪（如果没有则使用 base_salary）
                internal = c.internal_base_salary or 0
                base_salary = c.base_salary or 0
                base = internal if internal > 0 else base_salary
                # 公式：基本月薪 × 3 × 1.2
                monthly_cost = base * 3 * 1.2
                total_cost = monthly_cost * months
                
                consultant_internal_costs.append({
                    '顾问': c.name,
                    '团队': c.team,
                    '基本月薪': base,
                    '核算月数': months,
                    '月度成本': monthly_cost,
                    '总成本': total_cost
                })
                total_internal_cost += total_cost
        
        return {
            'total_cost': total_internal_cost,
            'months': months,
            'consultant_details': pd.DataFrame(consultant_internal_costs) if consultant_internal_costs else pd.DataFrame()
        }
    
    def _get_expense_by_category(self, expenses: List[Expense], 
                                  consultant_costs: float) -> pd.DataFrame:
        """按类别统计费用"""
        df = pd.DataFrame([{
            '类别': e.category,
            '金额': e.amount
        } for e in expenses])
        
        if not df.empty:
            summary = df.groupby('类别')['金额'].sum().reset_index()
        else:
            summary = pd.DataFrame(columns=['类别', '金额'])
        
        # 添加人力成本
        if consultant_costs > 0:
            personnel_row = pd.DataFrame([{'类别': '人力成本', '金额': consultant_costs}])
            summary = pd.concat([summary, personnel_row], ignore_index=True)
            
        return summary.sort_values('金额', ascending=False)
    
    def get_monthly_expense(self) -> pd.DataFrame:
        """月度费用趋势"""
        if not self.expenses:
            return pd.DataFrame(columns=['月份', '金额'])
            
        df = pd.DataFrame([{
            '月份': e.date.strftime('%Y-%m'),
            '金额': e.amount,
            '类别': e.category
        } for e in self.expenses])
        
        monthly = df.groupby('月份')['金额'].sum().reset_index()
        return monthly.sort_values('月份')
    
    def get_expense_by_department(self) -> pd.DataFrame:
        """按部门统计费用"""
        if not self.expenses:
            return pd.DataFrame(columns=['部门', '金额'])
            
        df = pd.DataFrame([{
            '部门': e.department if e.department else '未分类',
            '金额': e.amount
        } for e in self.expenses])
        
        summary = df.groupby('部门')['金额'].sum().reset_index()
        return summary.sort_values('金额', ascending=False)
    
    def get_expense_detail(self) -> pd.DataFrame:
        """费用明细"""
        if not self.expenses:
            return pd.DataFrame(columns=['费用编号', '日期', '费用类型', '金额', '部门', '备注'])
            
        df = pd.DataFrame([{
            '费用编号': e.expense_id,
            '日期': e.date.strftime('%Y-%m-%d'),
            '费用类型': e.category,
            '金额': e.amount,
            '部门': e.department if e.department else '-',
            '备注': e.note if e.note else '-'
        } for e in sorted(self.expenses, key=lambda x: x.date, reverse=True)])
        
        return df
    
    # ============ 利润分析 ============
    
    def get_profit_analysis(self, start_date: datetime = None,
                           end_date: datetime = None) -> Dict:
        """利润分析
        注意：total_collected 已包含上年遗留，利润基于此计算
        """
        revenue = self.get_revenue_summary(start_date, end_date)
        expense = self.get_expense_summary(start_date, end_date)
        
        # 总回款（已包含上年遗留）
        total_collected = revenue['total_collected']
        gross_profit = total_collected - expense['total_expense']
        profit_margin = gross_profit / total_collected * 100 if total_collected > 0 else 0
        
        return {
            'total_revenue': revenue['total_fee'],
            'total_collected': total_collected,  # 总回款（含上年遗留）
            'prior_year_collection': revenue['prior_year_collection'],  # 其中：上年遗留
            'current_year_collection': revenue['current_year_collection'],  # 其中：本年回款
            'total_expense': expense['total_expense'],
            'gross_profit': gross_profit,
            'profit_margin': profit_margin
        }
    
    def get_internal_profit_analysis(self, start_date: datetime = None,
                                     end_date: datetime = None) -> Dict:
        """
        内部核算版本：利润分析（给顾问展示的盈亏分析）
        使用内部核算的顾问成本，不包含真实运营费用
        """
        revenue = self.get_revenue_summary(start_date, end_date)
        expense = self.get_internal_expense_summary(start_date, end_date)
        
        # 总回款（已包含上年遗留）
        total_collected = revenue['total_collected']
        gross_profit = total_collected - expense['consultant_cost']
        profit_margin = gross_profit / total_collected * 100 if total_collected > 0 else 0
        
        return {
            'total_revenue': revenue['total_fee'],
            'total_collected': total_collected,  # 总回款（含上年遗留）
            'prior_year_collection': revenue['prior_year_collection'],  # 其中：上年遗留
            'current_year_collection': revenue['current_year_collection'],  # 其中：本年回款
            'consultant_cost': expense['consultant_cost'],
            'total_expense': expense['consultant_cost'],  # 内部版本只显示顾问成本
            'gross_profit': gross_profit,
            'profit_margin': profit_margin,
            'months': expense['months'],
            'consultant_details': expense['consultant_details'],
            'is_internal': True
        }
    
    def get_monthly_profit(self) -> pd.DataFrame:
        """月度利润趋势
        注意：回款金额已包含上年遗留
        """
        revenue = self.get_monthly_revenue()
        expense = self.get_monthly_expense()
        
        merged = pd.merge(revenue, expense, on='月份', how='outer').fillna(0)
        # 利润 = 总回款 - 费用
        merged['利润'] = merged['回款金额'] - merged['金额']
        # 避免除以0：回款为0时，利润率显示为0
        merged['利润率'] = merged.apply(
            lambda row: (row['利润'] / row['回款金额'] * 100) if row['回款金额'] > 0 else 0, 
            axis=1
        )
        
        return merged.sort_values('月份')
    
    # ============ KPI 分析 ============
    
    def get_kpi_dashboard(self) -> Dict:
        """KPI仪表板"""
        if not self.deals:
            return {
                'deal_count': 0,
                'success_rate': 0,
                'avg_collection_days': 0,
                'client_retention': 0,
                'avg_fee_rate': 20,
                'top_consultant': '-'
            }
        
        # 成单数
        deal_count = len(self.deals)
        
        # 平均费率
        avg_fee_rate = sum(d.fee_rate for d in self.deals) / len(self.deals)
        
        # 平均回款周期
        collection_days = []
        for d in self.deals:
            if d.payment_date and d.deal_date:
                days = (d.payment_date - d.deal_date).days
                if days >= 0:
                    collection_days.append(days)
        avg_collection_days = sum(collection_days) / len(collection_days) if collection_days else 0
        
        # 客户复购率
        client_deals = {}
        for d in self.deals:
            client_deals[d.client_name] = client_deals.get(d.client_name, 0) + 1
        repeat_clients = sum(1 for count in client_deals.values() if count > 1)
        client_retention = repeat_clients / len(client_deals) * 100 if client_deals else 0
        
        # 最佳顾问
        consultant_performance = self.get_revenue_by_consultant()
        top_consultant = consultant_performance.iloc[0]['顾问'] if not consultant_performance.empty else '-'
        
        return {
            'deal_count': deal_count,
            'avg_fee_rate': avg_fee_rate,
            'avg_collection_days': avg_collection_days,
            'client_retention': client_retention,
            'top_consultant': top_consultant
        }
    
    def get_consultant_performance(self) -> pd.DataFrame:
        """顾问绩效详情"""
        if not self.deals or not self.consultants:
            return pd.DataFrame()
        
        revenue_by_consultant = self.get_revenue_by_consultant()
        
        # 合并顾问信息
        consultant_df = pd.DataFrame([{
            '顾问': c.name,
            '底薪': c.base_salary,
            '团队': c.team,
            '月度KPI': c.monthly_kpi
        } for c in self.consultants])
        
        merged = pd.merge(revenue_by_consultant, consultant_df, on='顾问', how='outer').fillna(0)
        
        # 计算KPI完成率（假设数据周期为3个月）
        merged['KPI完成率'] = (merged['佣金总额'] / (merged['月度KPI'] * 3) * 100).fillna(0)
        
        # 计算顾问成本
        merged['顾问成本'] = merged['底薪'] * 3 + merged['佣金总额'] * 0.30
        
        # 计算贡献利润
        merged['贡献利润'] = merged['佣金总额'] - merged['顾问成本']
        
        return merged.sort_values('佣金总额', ascending=False)
    
    # ============ 辅助方法 ============
    
    def _filter_deals_by_date(self, start_date: datetime = None,
                              end_date: datetime = None) -> List[Deal]:
        """按日期筛选成单"""
        deals = self.deals
        if start_date:
            deals = [d for d in deals if d.deal_date and d.deal_date >= start_date]
        if end_date:
            deals = [d for d in deals if d.deal_date and d.deal_date <= end_date]
        return deals
    
    def _filter_expenses_by_date(self, start_date: datetime = None,
                                 end_date: datetime = None) -> List[Expense]:
        """按日期筛选费用"""
        expenses = self.expenses
        if start_date:
            expenses = [e for e in expenses if e.date and e.date >= start_date]
        if end_date:
            expenses = [e for e in expenses if e.date and e.date <= end_date]
        return expenses
    
    # ============ 预测收入分析 ============
    
    def get_forecast_summary(self) -> Dict:
        """预测收入汇总"""
        if not self.forecasts:
            return {
                'total_forecasts': 0,
                'total_estimated_fee': 0,
                'weighted_revenue': 0,
                'estimated_profit': 0,
                'avg_success_rate': 0
            }
        
        total_estimated_fee = sum(f.estimated_fee or (f.estimated_salary * f.fee_rate / 100) for f in self.forecasts)
        weighted_revenue = sum(f.weighted_revenue for f in self.forecasts)
        estimated_profit = sum(f.estimated_profit for f in self.forecasts)
        avg_success_rate = sum(f.success_rate for f in self.forecasts) / len(self.forecasts)
        
        return {
            'total_forecasts': len(self.forecasts),
            'total_estimated_fee': total_estimated_fee,
            'weighted_revenue': weighted_revenue,
            'estimated_profit': estimated_profit,
            'avg_success_rate': avg_success_rate
        }
    
    def get_forecast_by_consultant(self) -> pd.DataFrame:
        """按顾问统计预测收入"""
        if not self.forecasts:
            return pd.DataFrame(columns=['顾问', '在途单数', '预计佣金总额', '加权预测收入', '平均成功率'])
        
        df = pd.DataFrame([{
            '顾问': f.consultant or '未知',
            '预计佣金': f.estimated_fee or (f.estimated_salary * f.fee_rate / 100),
            '加权收入': f.weighted_revenue,
            '成功率': f.success_rate
        } for f in self.forecasts])
        
        summary = df.groupby('顾问').agg({
            '预计佣金': 'sum',
            '加权收入': 'sum',
            '成功率': 'mean'
        }).reset_index()
        summary['在途单数'] = df.groupby('顾问').size().values
        summary.columns = ['顾问', '预计佣金总额', '加权预测收入', '平均成功率', '在途单数']
        summary = summary.sort_values('加权预测收入', ascending=False)
        
        return summary
    
    def get_forecast_by_stage(self) -> pd.DataFrame:
        """按阶段统计预测收入"""
        if not self.forecasts:
            return pd.DataFrame(columns=['阶段', '数量', '预计佣金', '加权收入', '平均成功率'])
        
        df = pd.DataFrame([{
            '阶段': f.stage or '未知',
            '预计佣金': f.estimated_fee or (f.estimated_salary * f.fee_rate / 100),
            '加权收入': f.weighted_revenue,
            '成功率': f.success_rate
        } for f in self.forecasts])
        
        summary = df.groupby('阶段').agg({
            '预计佣金': 'sum',
            '加权收入': 'sum',
            '成功率': 'mean'
        }).reset_index()
        summary['数量'] = df.groupby('阶段').size().values
        summary.columns = ['阶段', '预计佣金', '加权收入', '平均成功率', '数量']
        summary = summary.sort_values('加权收入', ascending=False)
        
        return summary
    
    def get_forecast_timeline(self) -> pd.DataFrame:
        """预测收入时间线（按预计成交日期）"""
        if not self.forecasts:
            return pd.DataFrame(columns=['月份', '数量', '预计佣金', '加权收入'])
        
        # 过滤掉没有预计成交日期的
        forecasts_with_date = [f for f in self.forecasts if f.expected_close_date]
        if not forecasts_with_date:
            return pd.DataFrame(columns=['月份', '数量', '预计佣金', '加权收入'])
        
        df = pd.DataFrame([{
            '月份': f.expected_close_date.strftime('%Y-%m'),
            '预计佣金': f.estimated_fee or (f.estimated_salary * f.fee_rate / 100),
            '加权收入': f.weighted_revenue
        } for f in forecasts_with_date])
        
        summary = df.groupby('月份').agg({
            '预计佣金': 'sum',
            '加权收入': 'sum'
        }).reset_index()
        summary['数量'] = df.groupby('月份').size().values
        summary.columns = ['月份', '预计佣金', '加权收入', '数量']
        summary = summary.sort_values('月份')
        
        return summary
    
    def get_forecast_detail(self) -> pd.DataFrame:
        """预测收入明细"""
        if not self.forecasts:
            return pd.DataFrame(columns=['编号', '客户', '职位', '顾问', '预计年薪', '费率', '预计佣金', '成功率', '加权收入', '阶段', '预计成交日期'])
        
        df = pd.DataFrame([{
            '编号': f.forecast_id,
            '客户': f.client_name,
            '职位': f.position,
            '顾问': f.consultant,
            '预计年薪': f.estimated_salary,
            '费率': f.fee_rate,
            '预计佣金': f.estimated_fee or (f.estimated_salary * f.fee_rate / 100),
            '成功率': f.success_rate,
            '加权收入': f.weighted_revenue,
            '阶段': f.stage,
            '预计成交日期': f.expected_close_date.strftime('%Y-%m-%d') if f.expected_close_date else '-'
        } for f in sorted(self.forecasts, key=lambda x: x.weighted_revenue, reverse=True)])
        
        return df
    
    def export_report(self, filepath: str):
        """导出Excel报告"""
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # 收入汇总
            revenue_summary = self.get_revenue_summary()
            pd.DataFrame([revenue_summary]).to_excel(writer, sheet_name='收入汇总', index=False)
            
            # 月度趋势
            self.get_monthly_revenue().to_excel(writer, sheet_name='月度收入', index=False)
            
            # 顾问业绩
            self.get_revenue_by_consultant().to_excel(writer, sheet_name='顾问业绩', index=False)
            
            # 客户分析
            self.get_revenue_by_client().to_excel(writer, sheet_name='客户分析', index=False)
            
            # 利润分析
            profit_df = self.get_monthly_profit()
            profit_df.to_excel(writer, sheet_name='利润分析', index=False)
            
            # 成单明细
            deals_df = pd.DataFrame([{
                '成单ID': d.deal_id or '',
                '客户': d.client_name or '',
                '候选人': d.candidate_name or '',
                '职位': d.position or '',
                '顾问': d.consultant or '',
                '成单日期': d.deal_date.strftime('%Y-%m-%d') if d.deal_date else '',
                '年薪': d.annual_salary if (d.annual_salary or 0) > 0 else '',
                '费率': d.fee_rate if (d.fee_rate or 0) != 20 else '',
                '佣金': d.fee_amount or 0,
                '回款状态': d.payment_status or '',
                '实际回款(总)': d.actual_payment or 0,
                '其中：上年遗留': d.prior_year_collection if (d.prior_year_collection or 0) > 0 else '',
                '其中：本年回款': (d.actual_payment or 0) - (d.prior_year_collection or 0)
            } for d in self.deals])
            deals_df.to_excel(writer, sheet_name='成单明细', index=False)
            
            # 费用明细
            if self.expenses:
                self.get_expense_detail().to_excel(writer, sheet_name='费用明细', index=False)
                
                # 费用按类型统计
                expense_by_category = self._get_expense_by_category(self.expenses, 0)
                expense_by_category.to_excel(writer, sheet_name='费用类型统计', index=False)
                
                # 费用按部门统计
                expense_by_dept = self.get_expense_by_department()
                if not expense_by_dept.empty:
                    expense_by_dept.to_excel(writer, sheet_name='费用部门统计', index=False)
            
            # 预测收入数据
            if self.forecasts:
                # 预测汇总
                forecast_summary = self.get_forecast_summary()
                pd.DataFrame([forecast_summary]).to_excel(writer, sheet_name='预测汇总', index=False)
                
                # 预测明细
                self.get_forecast_detail().to_excel(writer, sheet_name='预测明细', index=False)
                
                # 顾问预测统计
                self.get_forecast_by_consultant().to_excel(writer, sheet_name='顾问预测', index=False)
                
                # 阶段预测统计
                self.get_forecast_by_stage().to_excel(writer, sheet_name='阶段预测', index=False)


def create_sample_data():
    """创建示例数据"""
    np.random.seed(42)
    
    # 顾问数据
    consultants_data = {
        'name': ['张三', '李四', '王五', '赵六', '陈七'],
        'base_salary': [8000, 10000, 12000, 8000, 15000],
        'join_date': ['2023-01-15', '2023-03-01', '2022-08-20', '2023-06-01', '2022-05-10'],
        'team': ['互联网', '互联网', '金融', '金融', '高端制造'],
        'is_active': [True, True, True, True, True],
        'monthly_kpi': [50000, 60000, 80000, 50000, 100000]
    }
    
    # 成单数据（最近6个月）
    clients = ['阿里巴巴', '腾讯', '字节跳动', '美团', '京东', '蚂蚁集团', '招商银行', '平安科技']
    positions = ['Java开发', '产品经理', '算法工程师', '前端开发', '数据分析师', 'HR总监', '财务经理']
    consultants = ['张三', '李四', '王五', '赵六', '陈七']
    
    deals_data = []
    deal_id = 1
    
    for month_offset in range(6):
        month_date = datetime.now() - timedelta(days=30*month_offset)
        month_deals = np.random.randint(5, 15)  # 每月5-15单
        
        for _ in range(month_deals):
            deal_date = month_date - timedelta(days=np.random.randint(0, 30))
            annual_salary = np.random.randint(200000, 800000)
            fee_rate = np.random.choice([18, 20, 22, 25])
            fee_amount = annual_salary * fee_rate / 100
            
            # 回款状态
            days_since = (datetime.now() - deal_date).days
            if days_since > 60:
                payment_status = '已回款'
                actual_payment = fee_amount
                payment_date = deal_date + timedelta(days=np.random.randint(30, 60))
            elif days_since > 30:
                payment_status = np.random.choice(['部分回款', '已回款'])
                actual_payment = fee_amount * np.random.choice([0.5, 1.0]) if payment_status == '部分回款' else fee_amount
                payment_date = deal_date + timedelta(days=np.random.randint(30, days_since)) if actual_payment > 0 else None
            else:
                payment_status = '未回款'
                actual_payment = 0
                payment_date = None
            
            deals_data.append({
                'deal_id': f'D{deal_id:04d}',
                'client_name': np.random.choice(clients),
                'candidate_name': f'候选人{deal_id}',
                'position': np.random.choice(positions),
                'consultant': np.random.choice(consultants),
                'deal_date': deal_date.strftime('%Y-%m-%d'),
                'annual_salary': annual_salary,
                'fee_rate': fee_rate,
                'fee_amount': fee_amount,
                'payment_status': payment_status,
                'actual_payment': actual_payment,
                'payment_date': payment_date.strftime('%Y-%m-%d') if payment_date else None
            })
            deal_id += 1
    
    # 费用数据
    expense_categories = ['租金', '工资', '营销', '办公', '其他']
    expenses_data = []
    expense_id = 1
    
    for month_offset in range(6):
        month_date = datetime.now() - timedelta(days=30*month_offset)
        
        for category in expense_categories:
            if category == '租金':
                amount = 30000
            elif category == '工资':
                amount = np.random.randint(80000, 100000)  # 运营人员工资
            elif category == '营销':
                amount = np.random.randint(5000, 20000)
            elif category == '办公':
                amount = np.random.randint(3000, 8000)
            else:
                amount = np.random.randint(1000, 5000)
            
            expenses_data.append({
                'expense_id': f'E{expense_id:04d}',
                'category': category,
                'amount': amount,
                'date': month_date.strftime('%Y-%m-%d'),
                'description': f'{category}支出'
            })
            expense_id += 1
    
    return (
        pd.DataFrame(consultants_data),
        pd.DataFrame(deals_data),
        pd.DataFrame(expenses_data)
    )
