#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
猎头公司财务分析工具 - 完整版
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models import AdvancedRecruitmentAnalyzer, PositionLifecycle, CashFlowEvent
from alert_page import render_alert_system
from pages.real_finance_page import render_real_finance_page
import auto_import

st.set_page_config(
    page_title="猎头财务分析工具",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.main-header {
    font-size: 2.2rem;
    font-weight: bold;
    color: #1E3A8A;
    margin-bottom: 0.5rem;
}
.sub-header {
    font-size: 1rem;
    color: #6B7280;
    margin-bottom: 1.5rem;
}
</style>
""", unsafe_allow_html=True)

def format_currency(value):
    """格式化货币显示"""
    if pd.isna(value) or value is None:
        return "¥0"
    if abs(value) >= 10000:
        return f"¥{value/10000:.1f}万"
    return f"¥{value:,.0f}"

def format_percent(value):
    """格式化百分比显示"""
    if pd.isna(value) or value is None:
        return "0.0%"
    return f"{value*100:.1f}%"


def render_sidebar():
    """渲染侧边栏"""
    st.sidebar.markdown("<div style='font-size: 1.5rem; font-weight: bold; color: #1E3A8A;'>📊 数据配置</div>", unsafe_allow_html=True)
    
    analyzer = st.session_state.analyzer
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📁 数据上传")
    
    # 成单数据上传
    deal_file = st.sidebar.file_uploader("成单数据 (Excel)", type=['xlsx', 'xls'], key='deal_file')
    if deal_file:
        try:
            df_deals = pd.read_excel(deal_file)
            analyzer.load_positions_from_dataframe(df_deals)
            st.sidebar.success(f"✓ 成单数据: {len(df_deals)}条")
        except Exception as e:
            st.sidebar.error(f"× 加载失败: {e}")
    
    # 顾问数据上传
    consultant_file = st.sidebar.file_uploader("顾问数据 (Excel)", type=['xlsx', 'xls'], key='consultant_file')
    if consultant_file:
        try:
            df_consultants = pd.read_excel(consultant_file)
            # 清空现有顾问配置，防止重复叠加
            analyzer.consultant_configs = {}
            # 加载顾问配置
            for idx, row in df_consultants.iterrows():
                name = row.get('name')
                if pd.notna(name):
                    salary = float(row['base_salary']) if pd.notna(row.get('base_salary')) else 20000
                    is_active = bool(row.get('is_active', True))
                    analyzer.consultant_configs[name] = {
                        'monthly_salary': salary,
                        'is_active': is_active,
                        'salary_multiplier': 3.0
                    }
            st.sidebar.success(f"✓ 顾问数据: {len(df_consultants)}人")
        except Exception as e:
            st.sidebar.error(f"× 加载失败: {e}")
    
    # Forecast数据上传
    forecast_file = st.sidebar.file_uploader("Forecast数据 (Excel)", type=['xlsx'], key='forecast_file')
    if forecast_file:
        try:
            df_forecast = pd.read_excel(forecast_file)
            analyzer.load_forecast_from_dataframe(df_forecast)
            st.sidebar.success(f"✓ Forecast: {len(df_forecast)}条")
        except Exception as e:
            st.sidebar.error(f"× 加载失败: {e}")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔄 Gllue API 同步")
    
    with st.sidebar.expander("配置谷露 API", expanded=False):
        # API 配置
        gllue_base_url = st.text_input(
            "Gllue 域名",
            value=st.session_state.get('gllue_base_url', ''),
            placeholder="如: yourcompany.gllue.com",
            help="你的谷露系统域名，不需要 https:// 前缀"
        )
        gllue_api_key = st.text_input(
            "API 密钥",
            value=st.session_state.get('gllue_api_key', ''),
            type="password",
            placeholder="从谷露系统获取的 API Key"
        )
        
        # 同步日期范围
        sync_start_date = st.date_input(
            "开始日期",
            value=datetime.now() - timedelta(days=365),
            help="同步此日期之后的 Offer/入职数据"
        )
        sync_end_date = st.date_input(
            "结束日期",
            value=datetime.now(),
            help="同步此日期之前的 Offer/入职数据"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 保存", use_container_width=True):
                st.session_state.gllue_base_url = gllue_base_url
                st.session_state.gllue_api_key = gllue_api_key
                st.success("已保存")
        
        with col2:
            if st.button("🔌 测试", use_container_width=True):
                if not gllue_base_url or not gllue_api_key:
                    st.error("请填写域名和密钥")
                else:
                    with st.spinner("测试中..."):
                        try:
                            import sys
                            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                            from gllue_client import GllueConfig, GllueAPIClient
                            
                            config = GllueConfig(
                                base_url=gllue_base_url,
                                api_key=gllue_api_key
                            )
                            client = GllueAPIClient(config)
                            test_data = client.get_users()
                            st.success(f"连接成功！{len(test_data)} 个用户")
                        except Exception as e:
                            st.error(f"连接失败: {str(e)[:50]}")
        
        if st.button("🚀 同步数据", type="primary", use_container_width=True):
            if not gllue_base_url or not gllue_api_key:
                st.error("请填写域名和密钥")
            else:
                with st.spinner("正在同步..."):
                    try:
                        import sys
                        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        from gllue_client import GllueConfig, GllueAPIClient
                        
                        config = GllueConfig(
                            base_url=gllue_base_url,
                            api_key=gllue_api_key
                        )
                        client = GllueAPIClient(config)
                        
                        stats = client.sync_to_finance_analyzer(
                            analyzer,
                            start_date=sync_start_date.strftime('%Y-%m-%d'),
                            end_date=sync_end_date.strftime('%Y-%m-%d')
                        )
                        
                        st.success(f"同步完成！Offer: {stats['offers_fetched']}, 入职: {stats['onboards_fetched']}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"同步失败: {str(e)[:100]}")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔄 自动同步")
    
    with st.sidebar.expander("文件夹自动监控", expanded=False):
        watched_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'watched')
        watched_base = os.path.abspath(watched_base)
        auto_import.ensure_watched_dirs(watched_base)
        
        st.write(f"**监控目录:** `{watched_base}`")
        
        if st.button("🔄 立即扫描", use_container_width=True, key="auto_scan_btn"):
            with st.spinner("扫描中..."):
                results = auto_import.scan_and_import(analyzer, watched_base)
                if results:
                    for r in results:
                        if r['status'] == 'success':
                            st.success(f"✓ [{r['type']}] {r['file']}: {r['message']}")
                        elif r['status'] == 'failed':
                            st.error(f"× {r['file']}: {r['message']}")
                        else:
                            st.info(f"- {r['file']}: {r['message']}")
                else:
                    st.info("未发现新文件")
        
        history = auto_import.get_import_history(watched_base)
        if history:
            st.write("**最近导入记录:**")
            for h in history[:5]:
                st.caption(f"{h['imported_at'][:10]} | {h['type']} | {h['file']} ({h['rows']}行)")
        
        if st.button("🗑️ 清空导入记录", type="secondary", use_container_width=True, key="clear_import_log_btn"):
            auto_import.clear_import_log(watched_base)
            st.success("已清空，下次扫描将重新导入所有文件")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ 基础配置")
    
    # 核算模式切换
    if 'use_real_costs' not in analyzer.config:
        analyzer.config['use_real_costs'] = False
    mode_options = {False: "假设模式 (3倍工资估算)", True: "真实财务模式 (实际工资/报销)"}
    current_mode = analyzer.config.get('use_real_costs', False)
    selected_mode = st.sidebar.radio(
        "核算模式",
        options=[False, True],
        format_func=lambda x: mode_options[x],
        index=0 if not current_mode else 1,
        key="cost_mode_radio"
    )
    if selected_mode != current_mode:
        analyzer.config['use_real_costs'] = selected_mode
        st.sidebar.success(f"已切换到: {mode_options[selected_mode]}")
        st.rerun()
    
    # 现金储备
    if 'cash_reserve' not in analyzer.config:
        analyzer.config['cash_reserve'] = 1800000
    analyzer.config['cash_reserve'] = st.sidebar.number_input(
        "现金储备 (元)",
        value=int(analyzer.config['cash_reserve']),
        step=100000
    )
    
    # 工资倍数
    if 'salary_multiplier' not in analyzer.config:
        analyzer.config['salary_multiplier'] = 3.0
    analyzer.config['salary_multiplier'] = st.sidebar.slider(
        "成本倍数 (工资×N)",
        min_value=2.0, max_value=5.0, value=3.0, step=0.5,
        help="包含社保、办公费用等的综合倍数"
    )
    
    st.sidebar.markdown("---")
    
    # 数据摘要
    if analyzer.positions or analyzer.forecast_positions or analyzer.real_cost_records:
        st.sidebar.markdown("### 📈 数据摘要")
        if analyzer.positions:
            st.sidebar.write(f"- 成单数据: {len(analyzer.positions)}条")
        if analyzer.consultant_configs:
            active_count = sum(1 for c in analyzer.consultant_configs.values() if c.get('is_active', True))
            st.sidebar.write(f"- 在职顾问: {active_count}人")
        if analyzer.forecast_positions:
            st.sidebar.write(f"- Forecast: {len(analyzer.forecast_positions)}条")
        if analyzer.real_cost_records:
            real_summary = analyzer.get_real_cost_summary()
            st.sidebar.write(f"- 真实财务: {real_summary['record_count']}条")
    else:
        st.sidebar.info("👆 请先上传数据文件")


def render_dashboard():
    """渲染现金流安全分析页面"""
    st.markdown('<div class="main-header">💰 现金流安全分析</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">90天/180天现金流预测与风险预警</div>', unsafe_allow_html=True)
    
    analyzer = st.session_state.analyzer
    
    if not analyzer.positions:
        st.info("📊 请先在侧边栏上传成单数据")
        return
    
    # 设置当前实际现金余额（已回款可能已消耗，请根据实际余额调整）
    cash_reserve = analyzer.config.get('cash_reserve', 1800000)
    current_balance = st.sidebar.number_input(
        "当前现金余额 (元)",
        value=int(cash_reserve),
        step=100000,
        help="已回款可能已消耗，请填入当前实际现金余额（如180万）",
        key="home_current_balance"
    )
    
    # 获取分析结果
    safety = analyzer.get_cash_safety_analysis(current_balance=current_balance)
    
    # 顶部指标
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("当前现金余额", format_currency(safety['current_balance']))
    with col2:
        st.metric("已回款(本年)", format_currency(safety['collected_revenue']))
    with col3:
        st.metric("月度成本", format_currency(safety['monthly_cost']))
    with col4:
        st.metric("90天预测余额", format_currency(safety['balance_90d']))
    with col5:
        st.metric("90天回款", format_currency(safety['future_90d_collected']))
    
    st.markdown("---")
    
    # 90天/180天余额卡片
    col1, col2 = st.columns(2)
    
    with col1:
        color_90d = safety['color_90d']
        # 财务恒等式展示
        formula_90d = f"""
        <div style="background: #f8f9fa; border-radius: 12px; padding: 15px; margin-top: 15px; font-size: 0.85rem; color: #666;">
            <div style="font-weight: bold; margin-bottom: 8px;">💰 财务恒等式（90天）</div>
            <div>期初余额: {format_currency(safety['current_balance'])}</div>
            <div style="color: #10B981;">+ 90天回款: {format_currency(safety['future_90d_collected'])}</div>
            <div style="color: #10B981;">+ Forecast: {format_currency(safety['forecast_90d'])}</div>
            <div style="color: #EF4444;">- 3个月成本: {format_currency(safety['monthly_cost'] * 3)}</div>
            <div style="border-top: 1px solid #ddd; margin-top: 8px; padding-top: 8px; font-weight: bold; color: #333;">
                = 期末余额: {format_currency(safety['balance_90d'])}
            </div>
        </div>
        """
        st.markdown(f"""
        <div style="background: {color_90d}; border-radius: 16px; padding: 30px; color: white; text-align: center;">
            <div style="font-size: 3rem; font-weight: bold;">{format_currency(safety['balance_90d'])}</div>
            <div style="font-size: 1.2rem; margin-top: 10px;">90天预测余额 ({safety['status_90d']})</div>
        </div>
        {formula_90d}
        """, unsafe_allow_html=True)
    
    with col2:
        color_180d = safety['color_180d']
        # 财务恒等式展示
        formula_180d = f"""
        <div style="background: #f8f9fa; border-radius: 12px; padding: 15px; margin-top: 15px; font-size: 0.85rem; color: #666;">
            <div style="font-weight: bold; margin-bottom: 8px;">💰 财务恒等式（180天）</div>
            <div>期初余额: {format_currency(safety['current_balance'])}</div>
            <div style="color: #10B981;">+ 180天回款: {format_currency(safety['future_180d_collected'])}</div>
            <div style="color: #10B981;">+ Forecast: {format_currency(safety['forecast_180d'])}</div>
            <div style="color: #F59E0B;">+ 已逾期: {format_currency(safety.get('overdue_collected', 0))}</div>
            <div style="color: #EF4444;">- 6个月成本: {format_currency(safety['monthly_cost'] * 6)}</div>
            <div style="border-top: 1px solid #ddd; margin-top: 8px; padding-top: 8px; font-weight: bold; color: #333;">
                = 期末余额: {format_currency(safety['balance_180d'])}
            </div>
        </div>
        """
        st.markdown(f"""
        <div style="background: {color_180d}; border-radius: 16px; padding: 30px; color: white; text-align: center;">
            <div style="font-size: 3rem; font-weight: bold;">{format_currency(safety['balance_180d'])}</div>
            <div style="font-size: 1.2rem; margin-top: 10px;">180天预测余额 ({safety['status_180d']})</div>
        </div>
        {formula_180d}
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 结论
    runway = safety['runway_months']
    st.markdown("### 📋 分析结论")
    
    # 红线 = 5个月储备金
    if runway >= 5:
        st.success(f"**现金储备可覆盖约 {runway:.1f} 个月成本。** 高于5个月红线，现金流状况良好。")
    elif runway >= 3:
        st.warning(f"**现金储备可覆盖约 {runway:.1f} 个月成本。** 低于5个月红线，建议关注回款进度。")
    else:
        st.error(f"**现金储备仅能覆盖约 {runway:.1f} 个月成本。** 远低于5个月红线，建议立即催收并控制支出。")


def format_consultant_details(details: dict):
    """渲染顾问核算明细（拆分：实际回款 | Offer待回 | Forecast）"""
    st.markdown(f"**📅 核算周期：** {details['period']}")
    
    # 成本明细
    cost = details['cost_details']
    st.markdown("##### 💰 成本计算")
    col1, col2, col3 = st.columns(3)
    col1.metric("月薪", f"{cost['monthly_salary']:,.0f}")
    col2.metric("成本倍数", f"×{cost['salary_multiplier']}")
    col3.metric("90天成本", f"{cost['cost_90d']:,.0f}")
    st.caption(f"计算公式：{cost['calculation']}")
    
    # ========== 实际回款明细 ==========
    st.markdown(f"##### ✅ 实际已回款明细 ({details['actual_collection_count']}笔)")
    if details['actual_collection_details']:
        df_actual = pd.DataFrame(details['actual_collection_details'])
        df_actual.columns = ['职位ID', '客户', '职位名称', '回款金额', '回款日期', '剩余天数', '状态']
        df_actual['回款金额'] = df_actual['回款金额'].apply(lambda x: f"{x:,.0f}")
        st.dataframe(df_actual, use_container_width=True, hide_index=True)
        st.success(f"**实际回款合计：{details['actual_collection']:,.0f}元，利润：{details['actual_profit']:,.0f}元，利润率：{details['actual_margin']}**")
    else:
        st.warning("暂无90天内实际回款记录")
    
    # ========== Offer待回明细 ==========
    st.markdown(f"##### 📝 Offer未回款明细 ({details['offer_pending_count']}笔)")
    if details['offer_pending_details']:
        df_offer = pd.DataFrame(details['offer_pending_details'])
        df_offer.columns = ['职位ID', '客户', '职位名称', '预期金额', '预计回款日', '剩余天数', '状态']
        df_offer['预期金额'] = df_offer['预期金额'].apply(lambda x: f"{x:,.0f}")
        st.dataframe(df_offer, use_container_width=True, hide_index=True)
        st.info(f"**含Offer待回后：收入 {details['offer_revenue']:,.0f}元，利润：{details['offer_profit']:,.0f}元，利润率：{details['offer_margin']}**")
    else:
        st.info("暂无90天内Offer待回款记录")
    
    # ========== Forecast明细 ==========
    st.markdown(f"##### 📋 90天Forecast明细 ({details['forecast_count']}笔)")
    if details['forecast_details']:
        df_fore = pd.DataFrame(details['forecast_details'])
        df_fore.columns = ['Forecast ID', '客户', '职位', '预估费用', '成功率', '加权收入', '预期回款日', '剩余天数', '阶段']
        df_fore['预估费用'] = df_fore['预估费用'].apply(lambda x: f"{x:,.0f}")
        df_fore['加权收入'] = df_fore['加权收入'].apply(lambda x: f"{x:,.0f}")
        df_fore['成功率'] = df_fore['成功率'].apply(lambda x: f"{x*100:.0f}%")
        st.dataframe(df_fore, use_container_width=True, hide_index=True)
        st.info(f"**含Forecast后总收入：{details['total_revenue']:,.0f}元**")
    else:
        st.info("暂无90天内Forecast回款")
    
    # ========== 汇总对比 ==========
    st.markdown("---")
    st.markdown("##### 📊 盈亏汇总对比")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("实际回款利润", f"{details['actual_profit']:,.0f}", 
                 f"利润率 {details['actual_margin']}")
    with col2:
        st.metric("含Offer利润", f"{details['offer_profit']:,.0f}",
                 f"利润率 {details['offer_margin']}")
    with col3:
        st.metric("总预测利润", f"{details['net_profit']:,.0f}",
                 f"利润率 {details['profit_margin']}")
    
    # 计算过程
    st.markdown("##### 🧮 详细计算过程")
    for line in details['calculation_process']:
        st.markdown(f"- {line}")


def render_consultant_profit():
    """渲染顾问盈亏分析页面"""
    st.markdown('<div class="main-header">📊 顾问盈亏分析</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">90天滚动盈亏预测与风险评估（拆分：实际回款 | Offer待回 | Forecast）</div>', unsafe_allow_html=True)
    
    analyzer = st.session_state.analyzer
    
    if not analyzer.positions and not analyzer.forecast_positions:
        st.info("📊 请上传成单数据或Forecast数据")
        return
    
    forecast_df = analyzer.get_consultant_profit_forecast(forecast_days=90)
    
    if forecast_df.empty:
        st.warning("暂无足够数据生成分析")
        return
    
    # ========== 汇总指标（拆分展示）==========
    st.markdown("##### 💰 90天收入构成（拆分实际回款、Offer待回、Forecast）")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        actual_90d = forecast_df['已回款'].sum()
        st.metric("已回款", format_currency(actual_90d), 
                 help="已到账的回款（累计贡献）")
    with col2:
        offer_90d = forecast_df['90天Offer待回'].sum()
        st.metric("90天Offer待回", format_currency(offer_90d),
                 help="已成单但未回款的预期收入")
    with col3:
        forecast_90d = forecast_df['90天Forecast'].sum()
        st.metric("90天Forecast", format_currency(forecast_90d),
                 help="在途单的加权预期")
    with col4:
        total_revenue = forecast_df['预测总收入'].sum()
        st.metric("预测总收入", format_currency(total_revenue))
    
    # 累计贡献 vs 预期贡献 对比
    st.markdown("##### 📊 累计贡献 vs 预期贡献")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        actual_total = forecast_df['累计实际回款'].sum()
        st.metric("累计实际回款", format_currency(actual_total),
                 help="顾问历史累计已到账的回款总额")
    with col2:
        offer_total = forecast_df['累计Offer待回'].sum()
        st.metric("累计Offer待回", format_currency(offer_total),
                 help="顾问已成单但未回款的总额")
    with col3:
        forecast_total = forecast_df['累计Forecast'].sum()
        st.metric("累计Forecast", format_currency(forecast_total),
                 help="顾问在途单的加权预期总额")
    
    st.markdown("---")
    
    # ========== 顾问明细表格 ==========
    st.markdown("#### 📋 顾问明细")
    
    # 创建简化版展示表格
    display_cols = [
        '顾问',
        '已回款', '实际回款利润', '实际回款利润率',
        '90天Offer待回', '含Offer利润', '含Offer利润率',
        '90天Forecast', '预测净利润', '预测利润率',
        '风险评级'
    ]
    
    display_df = forecast_df[display_cols].copy()
    
    # 格式化金额列
    currency_cols = ['已回款', '90天Offer待回', '90天Forecast',
                     '实际回款利润', '含Offer利润', '预测净利润',
                     '累计实际回款', '累计Offer待回', '累计Forecast']
    for col in currency_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(format_currency)
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # ========== 可视化对比 ==========
    st.markdown("---")
    st.markdown("#### 📈 顾问收入构成对比")
    
    # 选择要对比的顾问
    selected_consultants = st.multiselect(
        "选择顾问进行对比（最多选择5人）",
        options=forecast_df['顾问'].tolist(),
        default=forecast_df.head(3)['顾问'].tolist(),
        max_selections=5,
        key="consultant_compare_select"
    )
    
    if selected_consultants:
        compare_df = forecast_df[forecast_df['顾问'].isin(selected_consultants)]
        
        # 堆叠柱状图：实际回款 vs Offer待回 vs Forecast
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='实际回款',
            x=compare_df['顾问'],
            y=compare_df['已回款'],
            marker_color='#10B981'
        ))
        fig.add_trace(go.Bar(
            name='Offer待回',
            x=compare_df['顾问'],
            y=compare_df['90天Offer待回'],
            marker_color='#3B82F6'
        ))
        fig.add_trace(go.Bar(
            name='Forecast',
            x=compare_df['顾问'],
            y=compare_df['90天Forecast'],
            marker_color='#F59E0B'
        ))
        
        fig.update_layout(
            title='90天收入构成对比（实际回款 | Offer待回 | Forecast）',
            barmode='stack',
            xaxis_title='顾问',
            yaxis_title='金额（元）',
            template='plotly_white',
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 利润率对比
        fig2 = go.Figure()
        
        # 转换利润率字符串为数值
        def parse_margin(margin_str):
            if margin_str == '-' or pd.isna(margin_str):
                return None
            try:
                return float(margin_str.replace('%', ''))
            except:
                return None
        
        compare_df_plot = compare_df.copy()
        compare_df_plot['实际利润率'] = compare_df_plot['实际回款利润率'].apply(parse_margin)
        compare_df_plot['含Offer利润率'] = compare_df_plot['含Offer利润率'].apply(parse_margin)
        compare_df_plot['总利润率'] = compare_df_plot['预测利润率'].apply(parse_margin)
        
        fig2.add_trace(go.Bar(
            name='仅实际回款',
            x=compare_df_plot['顾问'],
            y=compare_df_plot['实际利润率'],
            marker_color='#10B981'
        ))
        fig2.add_trace(go.Bar(
            name='含Offer待回',
            x=compare_df_plot['顾问'],
            y=compare_df_plot['含Offer利润率'],
            marker_color='#3B82F6'
        ))
        fig2.add_trace(go.Bar(
            name='含Forecast',
            x=compare_df_plot['顾问'],
            y=compare_df_plot['总利润率'],
            marker_color='#8B5CF6'
        ))
        
        fig2.update_layout(
            title='利润率对比（%）- 不同场景下的盈利能力',
            barmode='group',
            xaxis_title='顾问',
            yaxis_title='利润率 (%)',
            template='plotly_white',
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        # 添加20%利润目标线
        fig2.add_hline(y=20, line_dash="dash", line_color="red", 
                      annotation_text="20%目标线", annotation_position="right")
        
        st.plotly_chart(fig2, use_container_width=True)
    
    # 核算明细展开
    st.markdown("---")
    st.markdown("#### 🔍 顾问核算明细（点击展开查看详细核算过程）")
    
    consultants = forecast_df['顾问'].tolist()
    if consultants:
        selected_consultant = st.selectbox(
            "选择顾问查看核算明细",
            options=consultants,
            key="consultant_detail_select"
        )
        
        if selected_consultant:
            with st.expander(f"📊 {selected_consultant} 的90天盈亏核算明细", expanded=True):
                details = analyzer.get_consultant_profit_details(selected_consultant, forecast_days=90)
                format_consultant_details(details)
    
    # 风险分布
    st.markdown("---")
    st.markdown("#### 📊 风险评级分布")
    
    risk_counts = forecast_df['风险评级'].value_counts()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        healthy = sum(1 for r in risk_counts.index if '🟢' in str(r))
        st.metric("健康", healthy)
    with col2:
        warning = sum(1 for r in risk_counts.index if '🟡' in str(r))
        st.metric("低利润", warning)
    with col3:
        danger = sum(1 for r in risk_counts.index if '🔴' in str(r))
        st.metric("亏损风险", danger)


def render_forecast_analysis():
    """渲染Forecast预测分析页面"""
    st.markdown('<div class="main-header">📈 Forecast预测分析</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">在途单的加权预期价值与回款预测</div>', unsafe_allow_html=True)
    
    analyzer = st.session_state.analyzer
    
    if not analyzer.forecast_positions:
        st.info("📊 请上传Forecast预测数据")
        return
    
    summary = analyzer.get_forecast_summary()
    
    # 汇总指标
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("在途单数", summary['total_forecasts'])
    with col2:
        st.metric("预计佣金总额", format_currency(summary['total_estimated_fee']))
    with col3:
        st.metric("加权预测收入", format_currency(summary['weighted_revenue']))
    with col4:
        st.metric("平均成功率", f"{summary['avg_success_rate']:.1f}%")
    
    st.markdown("---")
    
    # 回款日期推算说明
    avg_cycle = analyzer.get_historical_payment_cycle()
    offer_to_payment = analyzer.AVG_OFFER_TO_ONBOARD_DAYS + avg_cycle
    
    st.info(f"""
    **Forecast回款日期推算：** Offer时间 + {analyzer.AVG_OFFER_TO_ONBOARD_DAYS}天(入职) + {avg_cycle}天(账期) = {offer_to_payment}天
    """)
    
    # 明细表
    st.markdown("#### 📋 Forecast明细")
    
    forecast_df = analyzer.get_forecast_analysis()
    
    # 筛选
    col1, col2 = st.columns(2)
    with col1:
        consultants = forecast_df['顾问'].unique().tolist()
        filter_consultant = st.multiselect("筛选顾问", options=consultants)
    with col2:
        stages = forecast_df['阶段'].unique().tolist()
        filter_stage = st.multiselect("筛选阶段", options=stages)
    
    filtered_df = forecast_df.copy()
    if filter_consultant:
        filtered_df = filtered_df[filtered_df['顾问'].isin(filter_consultant)]
    if filter_stage:
        filtered_df = filtered_df[filtered_df['阶段'].isin(filter_stage)]
    
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)


def render_cashflow_calendar():
    """渲染现金流日历页面"""
    st.markdown('<div class="main-header">📅 现金流日历</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">半月现金流预测与关键节点</div>', unsafe_allow_html=True)
    
    analyzer = st.session_state.analyzer
    
    if not analyzer.positions:
        st.info("📊 请上传成单数据")
        return
    
    # 计算参考数据
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    cash_reserve = analyzer.config.get('cash_reserve', 1800000)
    collected_revenue = sum(
        p.actual_payment for p in analyzer.positions
        if p.payment_date and p.payment_date.year == today.year and p.payment_date <= today
    )
    # 注：已回款可能已消耗，默认只使用现金储备作为初始余额
    default_balance = cash_reserve
    
    # 设置
    col1, col2 = st.columns(2)
    with col1:
        days = st.slider("预测天数", min_value=30, max_value=180, value=90)
    with col2:
        initial_balance = st.number_input(
            "初始现金余额", 
            value=int(default_balance),
            step=10000,
            help=f"现金储备: {cash_reserve:,.0f}元 | 本年已回款: {collected_revenue:,.0f}元（可能已消耗，请根据实际余额调整）"
        )
    
    st.markdown("---")
    
    # 说明逻辑
    st.info(f"💡 **现金流计算逻辑**：从初始余额 **{initial_balance:,.0f}元** 开始，未来回款按预计日期流入，成本按日流出")
    
    # 半月汇总表格
    periods = 6 if days <= 90 else 12
    st.markdown(f"#### 未来{days}天现金流明细（按半月汇总）")
    
    biweekly = analyzer.generate_biweekly_cashflow_calendar(periods=periods, cash_reserve=initial_balance)
    
    # 格式化显示
    for col in ['确认流入', '预期流入', '确认流出', '预期流出', 
                '净现金流(确认)', '净现金流(预期)', '累计余额']:
        if col in biweekly.columns:
            biweekly[col] = biweekly[col].apply(format_currency)
    
    st.dataframe(biweekly, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # 关键节点
    st.markdown("#### 📍 关键现金流节点")
    
    # 催收预警
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    overdue = []
    due_7d = []
    
    for p in analyzer.positions:
        if not p.is_successful or p.payment_date:
            continue
        if not p.offer_date:
            continue
        
        expected_amount = p.actual_payment if p.actual_payment > 0 else p.fee_amount
        if expected_amount <= 0:
            continue
        
        payment_cycle = analyzer.get_position_payment_cycle(p)
        offer_to_payment_days = analyzer.AVG_OFFER_TO_ONBOARD_DAYS + payment_cycle
        est_date = p.offer_date + timedelta(days=offer_to_payment_days)
        days_until = (est_date - today).days
        
        item = {
            'client': p.client_name,
            'position': p.position_name,
            'consultant': p.consultant,
            'amount': expected_amount,
            'days': days_until
        }
        
        if days_until < 0:
            overdue.append(item)
        elif days_until <= 7:
            due_7d.append(item)
    
    if overdue:
        st.markdown("**🚨 已逾期回款：**")
        total_overdue = sum(i['amount'] for i in overdue)
        st.error(f"共 {len(overdue)} 笔，合计 {format_currency(total_overdue)}")
        for item in overdue[:5]:
            st.write(f"- {item['client']} - {item['consultant']}: {format_currency(item['amount'])} (逾期{abs(item['days'])}天)")
    
    if due_7d:
        st.markdown("**⚠️ 7天内到期：**")
        total_7d = sum(i['amount'] for i in due_7d)
        st.warning(f"共 {len(due_7d)} 笔，合计 {format_currency(total_7d)}")
    
    if not overdue and not due_7d:
        st.success("✅ 暂无紧急催款事项")


def render_whatif_simulator():
    """渲染情景模拟器 (What-if Analysis)"""
    st.markdown('<div class="main-header">🔮 情景模拟器</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">模拟经营决策对现金流的影响</div>', unsafe_allow_html=True)
    
    analyzer = st.session_state.analyzer
    
    if not analyzer.positions:
        st.info("📊 请上传成单数据以使用情景模拟功能")
        return
    
    # 获取基础数据
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    cash_reserve = analyzer.config.get('cash_reserve', 1800000)
    collected_revenue = sum(
        p.actual_payment for p in analyzer.positions
        if p.payment_date and p.payment_date.year == today.year and p.payment_date <= today
    )
    current_balance = cash_reserve
    
    # 显示当前基准
    st.markdown("#### 📊 当前基准")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("现金储备", format_currency(cash_reserve))
    with col2:
        st.metric("已回款(本年)", format_currency(collected_revenue))
    with col3:
        st.metric("当前现金余额", format_currency(current_balance))
    
    st.markdown("---")
    
    # 模拟1：人员变动
    st.markdown("#### 👥 模拟1：人员变动影响")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        headcount_change = st.number_input(
            "调整人数", min_value=-5, max_value=5, value=0,
            help="正数=招聘，负数=裁员"
        )
    with col2:
        headcount_salary = st.number_input(
            "人均月薪", min_value=5000, max_value=100000, value=20000, step=1000
        )
    with col3:
        headcount_effective = st.number_input(
            "生效天数", min_value=0, max_value=90, value=0,
            help="0=立即生效"
        )
    
    if headcount_change != 0:
        result = analyzer.simulate_headcount_change(
            headcount_change, headcount_salary, headcount_effective, forecast_days=180
        )
        
        impact_color = "#10B981" if result['adjusted_balance'] > result['base_balance'] else "#EF4444"
        
        st.markdown(f"""
        <div style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid {impact_color};">
            <strong>模拟结果：</strong>{'新增' if headcount_change > 0 else '减少'} {abs(headcount_change)} 人<br>
            月度成本变化: <strong>{format_currency(result['monthly_cost_change'])}/月</strong><br>
            180天总影响: <strong>{format_currency(result['total_cost_impact'])}</strong><br>
            调整后180天余额: <strong style="color: {impact_color};">{format_currency(result['adjusted_balance'])}</strong> 
            (原 {format_currency(result['base_balance'])})<br>
            建议: <strong>{result['recommendation']}</strong>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 模拟2：账期调整
    st.markdown("#### ⏱️ 模拟2：客户账期调整")
    
    col1, col2 = st.columns(2)
    with col1:
        clients = list(set(p.client_name for p in analyzer.positions if p.client_name))
        selected_client = st.selectbox("选择客户", clients[:10] if clients else ["无数据"])
    with col2:
        new_cycle = st.slider("新账期天数", min_value=30, max_value=180, value=90)
    
    if selected_client != "无数据":
        result = analyzer.simulate_payment_cycle_change(selected_client, new_cycle)
        
        st.markdown(f"""
        <div style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #3B82F6;">
            <strong>客户:</strong> {result['client_keyword']}<br>
            <strong>影响单数:</strong> {result['affected_count']} 笔<br>
            <strong>涉及金额:</strong> {format_currency(result['affected_amount'])}<br>
            <strong>账期调整:</strong> {result['old_cycle_days']}天 → {result['new_cycle_days']}天<br>
            <strong>影响:</strong> {result['impact_description']}<br>
            <strong>建议:</strong> {result['recommendation']}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 模拟3：回款加速
    st.markdown("#### 🚀 模拟3：催收加速效果")
    
    col1, col2 = st.columns(2)
    with col1:
        accel_rate = st.slider(
            "加速回款比例 (%)", min_value=0, max_value=100, value=30
        ) / 100
    with col2:
        days_ahead = st.slider("提前天数", min_value=15, max_value=90, value=30)
    
    result = analyzer.simulate_collection_acceleration(accel_rate, days_ahead)
    
    if result['overdue_count'] > 0:
        impact_color = "#10B981"
        st.markdown(f"""
        <div style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid {impact_color};">
            <strong>逾期款项:</strong> {result['overdue_count']} 笔，合计 {format_currency(result['overdue_total'])}<br>
            <strong>加速回收:</strong> {accel_rate*100:.0f}% = <strong>{format_currency(result['improved_amount'])}</strong><br>
            <strong>180天余额改善:</strong> {format_currency(result['base_balance'])} → <strong>{format_currency(result['new_balance'])}</strong><br>
            <strong>可覆盖成本:</strong> {result['monthly_cost_cover']:.1f} 个月<br>
            <strong>建议:</strong> {result['recommendation']}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.success("✅ 暂无逾期款项，无需催收加速")


def load_default_data(analyzer):
    """自动加载默认数据文件（用于部署后无需上传即可查看）"""
    import os
    
    # 数据文件路径（相对于app.py）
    base_path = os.path.join(os.path.dirname(__file__), '..', 'data_templates', 'analysis_db')
    # 兼容旧的中文路径
    legacy_path = os.path.join(os.path.dirname(__file__), '..', 'data_templates', '分析数据库')
    if not os.path.exists(base_path) and os.path.exists(legacy_path):
        base_path = legacy_path
    
    deal_file = os.path.join(base_path, '成单数据模板03.xlsx')
    consultant_file = os.path.join(base_path, '顾问数据模板03.xlsx')
    forecast_file = os.path.join(base_path, 'forecastassignment_202604020626.xlsx')
    
    # 加载成单数据
    if os.path.exists(deal_file) and not analyzer.positions:
        try:
            df_deals = pd.read_excel(deal_file)
            analyzer.load_positions_from_dataframe(df_deals)
        except Exception as e:
            st.error(f"加载成单数据失败: {e}")
    
    # 加载顾问数据
    if os.path.exists(consultant_file) and not analyzer.consultant_configs:
        try:
            df_consultants = pd.read_excel(consultant_file)
            analyzer.consultant_configs = {}
            for idx, row in df_consultants.iterrows():
                name = row.get('name')
                if pd.notna(name):
                    analyzer.consultant_configs[name] = {
                        'monthly_salary': float(row['base_salary']) if pd.notna(row.get('base_salary')) else 20000,
                        'is_active': bool(row.get('is_active', True)),
                        'salary_multiplier': 3.0
                    }
        except Exception as e:
            st.error(f"加载顾问数据失败: {e}")
    
    # 加载Forecast数据
    if os.path.exists(forecast_file) and not analyzer.forecast_positions:
        try:
            df_forecast = pd.read_excel(forecast_file)
            analyzer.load_forecast_from_dataframe(df_forecast)
        except Exception as e:
            st.error(f"加载Forecast数据失败: {e}")

def main():
    """主函数"""
    # 初始化 analyzer
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = AdvancedRecruitmentAnalyzer()
        # 首次启动时自动加载默认数据
        load_default_data(st.session_state.analyzer)
    
    # 渲染侧边栏
    render_sidebar()
    
    # 主内容区标签页
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "💰 现金流安全",
        "📊 顾问盈亏分析",
        "📈 Forecast预测",
        "📅 现金流日历",
        "🔮 情景模拟",
        "🔔 智能预警",
        "📒 真实财务",
    ])
    
    with tab1:
        render_dashboard()
    
    with tab2:
        render_consultant_profit()
    
    with tab3:
        render_forecast_analysis()
    
    with tab4:
        render_cashflow_calendar()
    
    with tab5:
        render_whatif_simulator()
    
    with tab6:
        render_alert_system(st.session_state.analyzer)
    
    with tab7:
        render_real_finance_page(st.session_state.analyzer)


if __name__ == "__main__":
    main()
