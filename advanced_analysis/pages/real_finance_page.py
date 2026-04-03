#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
真实财务分析页面
"""

import math
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from real_finance import (
    load_real_salary_from_dataframe,
    load_real_reimburse_from_dataframe,
    load_real_fixed_from_dataframe,
)


def format_currency(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "¥0"
    if abs(value) >= 10000:
        return f"¥{value/10000:.1f}万"
    return f"¥{value:,.0f}"


def render_real_finance_page(analyzer):
    st.markdown('<div class="main-header">📒 真实财务核算</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">基于真实工资、报销和固定支出的盈利能力分析</div>', unsafe_allow_html=True)
    
    # ========== 数据上传区 ==========
    st.markdown("### 📁 上传真实财务数据")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        salary_file = st.file_uploader("真实工资表", type=['xlsx', 'xls', 'csv'], key='real_salary_file')
        if salary_file:
            try:
                if salary_file.name.lower().endswith('.csv'):
                    df_sal = pd.read_csv(salary_file)
                else:
                    df_sal = pd.read_excel(salary_file)
                records = load_real_salary_from_dataframe(df_sal)
                analyzer.real_cost_records.extend(records)
                st.success(f"✓ 导入工资记录 {len(records)} 条")
            except Exception as e:
                st.error(f"× 导入失败: {e}")
    
    with col2:
        reimburse_file = st.file_uploader("真实报销/费用表", type=['xlsx', 'xls', 'csv'], key='real_reimburse_file')
        if reimburse_file:
            try:
                if reimburse_file.name.lower().endswith('.csv'):
                    df_rmb = pd.read_csv(reimburse_file)
                else:
                    df_rmb = pd.read_excel(reimburse_file)
                records = load_real_reimburse_from_dataframe(df_rmb)
                analyzer.real_cost_records.extend(records)
                st.success(f"✓ 导入报销记录 {len(records)} 条")
            except Exception as e:
                st.error(f"× 导入失败: {e}")
    
    with col3:
        fixed_file = st.file_uploader("固定支出表", type=['xlsx', 'xls', 'csv'], key='real_fixed_file')
        if fixed_file:
            try:
                if fixed_file.name.lower().endswith('.csv'):
                    df_fix = pd.read_csv(fixed_file)
                else:
                    df_fix = pd.read_excel(fixed_file)
                records = load_real_fixed_from_dataframe(df_fix)
                analyzer.real_cost_records.extend(records)
                st.success(f"✓ 导入固定支出 {len(records)} 条")
            except Exception as e:
                st.error(f"× 导入失败: {e}")
    
    # 清空按钮
    if st.button("🗑️ 清空已导入的真实财务数据", type="secondary"):
        analyzer.real_cost_records = []
        st.success("已清空真实财务数据")
        st.rerun()
    
    st.markdown("---")
    
    # ========== 汇总指标 ==========
    summary = analyzer.get_real_cost_summary()
    
    if not summary['has_data']:
        st.info("📊 请先上传真实财务数据（工资表、报销表、固定支出表）")
        return
    
    st.markdown("### 💰 真实财务汇总")
    
    c1, c2, c3, c4, c5 = st.columns(5)
    total_revenue = sum(p.actual_payment for p in analyzer.positions)
    total_cost = summary['total']
    real_profit = total_revenue - total_cost
    real_margin = (real_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    with c1:
        st.metric("累计回款", format_currency(total_revenue))
    with c2:
        st.metric("真实工资", format_currency(summary['salary']))
    with c3:
        st.metric("真实报销", format_currency(summary['reimburse']))
    with c4:
        st.metric("真实固定", format_currency(summary['fixed']))
    with c5:
        st.metric("真实总成本", format_currency(total_cost))
    
    st.markdown(f"**真实利润:** {format_currency(real_profit)}  &nbsp;&nbsp;|&nbsp;&nbsp; **真实利润率:** {real_margin:.1f}%")
    
    st.markdown("---")
    
    # ========== 月度盈亏表 ==========
    st.markdown("### 📅 月度真实盈亏")
    monthly_df = analyzer.get_monthly_real_summary_df()
    if not monthly_df.empty:
        # 添加累计列
        monthly_df['累计回款'] = monthly_df['回款'].cumsum()
        monthly_df['累计成本'] = monthly_df['真实总成本'].cumsum()
        monthly_df['累计利润'] = monthly_df['真实利润'].cumsum()
        
        display_cols = ['年月', '回款', '真实工资', '真实报销', '真实固定', '真实总成本', '真实利润']
        st.dataframe(monthly_df[display_cols], use_container_width=True, hide_index=True)
        
        # 月度趋势图
        fig = go.Figure()
        fig.add_trace(go.Bar(name='回款', x=monthly_df['年月'], y=monthly_df['回款'], marker_color='#10B981'))
        fig.add_trace(go.Bar(name='真实工资', x=monthly_df['年月'], y=monthly_df['真实工资'], marker_color='#EF4444'))
        fig.add_trace(go.Bar(name='真实报销', x=monthly_df['年月'], y=monthly_df['真实报销'], marker_color='#F59E0B'))
        fig.add_trace(go.Bar(name='真实固定', x=monthly_df['年月'], y=monthly_df['真实固定'], marker_color='#8B5CF6'))
        fig.add_trace(go.Scatter(name='真实利润', x=monthly_df['年月'], y=monthly_df['真实利润'], mode='lines+markers', line=dict(color='#1E3A8A', width=3)))
        fig.update_layout(
            title='月度真实收支与利润趋势',
            barmode='group',
            xaxis_title='年月',
            yaxis_title='金额（元）',
            template='plotly_white',
            height=450,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无足够数据生成月度汇总")
    
    st.markdown("---")
    
    # ========== 顾问真实盈亏 ==========
    st.markdown("### 👤 顾问真实盈亏")
    consultant_df = analyzer.get_consultant_real_profit_analysis()
    if not consultant_df.empty:
        st.dataframe(consultant_df, use_container_width=True, hide_index=True)
        
        # 顾问对比图
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(name='累计回款', x=consultant_df['顾问'], y=consultant_df['累计回款'], marker_color='#10B981'))
        fig2.add_trace(go.Bar(name='真实总成本', x=consultant_df['顾问'], y=consultant_df['真实总成本'], marker_color='#EF4444'))
        fig2.add_trace(go.Scatter(name='真实利润', x=consultant_df['顾问'], y=consultant_df['真实利润'], mode='lines+markers', line=dict(color='#1E3A8A', width=3)))
        fig2.update_layout(
            title='顾问真实盈亏对比',
            barmode='group',
            xaxis_title='顾问',
            yaxis_title='金额（元）',
            template='plotly_white',
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("暂无足够数据生成顾问分析")
    
    st.markdown("---")
    
    # ========== 职位真实边际贡献 ==========
    st.markdown("### 📋 职位真实边际贡献")
    if analyzer.positions:
        pos_real_df = analyzer.get_position_real_mc_analysis()
        if not pos_real_df.empty:
            st.dataframe(pos_real_df, use_container_width=True, hide_index=True)
        else:
            st.info("暂无职位真实边际贡献数据")
    else:
        st.info("请先上传成单数据")
    
    st.markdown("---")
    
    # ========== 假设 vs 真实 对比 ==========
    st.markdown("### ⚖️ 假设模式 vs 真实模式对比")
    
    if analyzer.positions:
        # 假设模式汇总
        mc_summary = analyzer.get_mc_summary()
        assumed_cost = mc_summary['total_direct_cost']
        assumed_profit = mc_summary['total_mc']
        
        # 真实模式汇总
        real_cost = summary['total']
        real_profit = total_revenue - real_cost
        
        diff_cost = real_cost - assumed_cost
        diff_profit = real_profit - assumed_profit
        
        compare_data = {
            '指标': ['累计回款', '总成本', '边际贡献/利润', '利润率'],
            '假设模式(3倍工资)': [
                format_currency(total_revenue),
                format_currency(assumed_cost),
                format_currency(assumed_profit),
                f"{(assumed_profit / total_revenue * 100):.1f}%" if total_revenue > 0 else '-',
            ],
            '真实财务模式': [
                format_currency(total_revenue),
                format_currency(real_cost),
                format_currency(real_profit),
                f"{(real_profit / total_revenue * 100):.1f}%" if total_revenue > 0 else '-',
            ],
            '差异': [
                '-',
                format_currency(diff_cost),
                format_currency(diff_profit),
                '-',
            ]
        }
        compare_df = pd.DataFrame(compare_data)
        st.dataframe(compare_df, use_container_width=True, hide_index=True)
        
        if diff_cost > 0:
            st.warning(f"⚠️ 真实总成本比假设模式高出 {format_currency(diff_cost)}，真实利润被低估可能意味着3倍工资倍数设定偏低，或近期有额外大额支出。")
        elif diff_cost < 0:
            st.info(f"✅ 真实总成本比假设模式低 {format_currency(abs(diff_cost))}，说明实际运营成本控制优于3倍工资假设。")
    else:
        st.info("请先上传成单数据以进行对比")
