"""
OKR分析和绩效工资计算页面
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from okr_analyzer import OKRDataLoader, OKRAnalyzer


def format_currency(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "¥0"
    if abs(value) >= 10000:
        return f"¥{value/10000:.1f}万"
    return f"¥{value:,.0f}"


def render_okr_page():
    """渲染OKR分析页面"""
    st.markdown('<div class="main-header">🎯 OKR分析与绩效工资</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">OKR目标达成情况与绩效工资核算</div>', unsafe_allow_html=True)
    
    # ========== 数据上传 ==========
    st.markdown("### 📁 上传OKR数据")
    
    col1, col2 = st.columns(2)
    with col1:
        okr_file = st.file_uploader("OKR考核表 (Excel)", type=['xlsx', 'xls'], key='okr_file')
    with col2:
        year = st.selectbox("年份", [2025, 2026], index=1)
        month = st.selectbox("月份", list(range(1, 13)), index=2)
    
    # 加载OKR数据
    okr_loader = None
    
    if okr_file:
        try:
            # 保存上传的文件到临时位置
            temp_path = f"/tmp/okr_upload_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
            with open(temp_path, "wb") as f:
                f.write(okr_file.getvalue())
            
            okr_loader = OKRDataLoader(temp_path)
            okr_loader.parse()
            
            # 存储到session_state
            st.session_state.okr_loader = okr_loader
            st.session_state.okr_year = year
            st.session_state.okr_month = month
            
            st.success(f"✅ 已加载 {len(okr_loader.consultant_okrs)} 位顾问的OKR数据")
        except Exception as e:
            st.error(f"加载OKR数据失败: {e}")
            return
    elif 'okr_loader' in st.session_state:
        okr_loader = st.session_state.okr_loader
        year = st.session_state.get('okr_year', year)
        month = st.session_state.get('okr_month', month)
    else:
        st.info("📊 请上传OKR考核表Excel文件")
        return
    
    # ========== 标签页 ==========
    tab1, tab2, tab3 = st.tabs(["📊 OKR汇总", "📋 指标明细", "🔍 系统数据对比"])
    
    # ---------- 汇总页 ----------
    with tab1:
        render_okr_summary(okr_loader)
    
    # ---------- 明细页 ----------
    with tab2:
        render_okr_detail(okr_loader)
    
    # ---------- 系统对比页 ----------
    with tab3:
        render_okr_system_comparison(okr_loader, year, month)


def render_okr_summary(okr_loader: OKRDataLoader):
    """渲染OKR汇总"""
    summary = okr_loader.get_summary_df()
    
    if summary.empty:
        st.warning("暂无OKR数据")
        return
    
    # KPI 卡片
    st.markdown("#### 📈 整体统计")
    
    total_bonus = summary['总发奖金'].sum()
    avg_bonus = summary['总发奖金'].mean()
    total_consultants = len(summary)
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("顾问人数", f"{total_consultants}人")
    with c2:
        st.metric("总发奖金", format_currency(total_bonus))
    with c3:
        st.metric("人均奖金", format_currency(avg_bonus))
    with c4:
        high_performers = len(summary[summary['平均完成率'] >= 1.0])
        st.metric("高绩效人数", f"{high_performers}人")
    
    st.markdown("---")
    
    # 团队汇总
    st.markdown("#### 👥 按团队汇总")
    team_summary = summary.groupby('团队').agg({
        '顾问': 'count',
        '月度奖金': 'sum',
        '总发奖金': 'sum',
        '平均完成率': 'mean',
    }).reset_index()
    team_summary.columns = ['团队', '人数', '月度奖金', '总发奖金', '平均完成率']
    team_summary['平均完成率'] = team_summary['平均完成率'].apply(lambda x: f"{x*100:.1f}%")
    
    st.dataframe(team_summary, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # 顾问排名
    st.markdown("#### 🏆 顾问绩效排名")
    
    sort_by = st.selectbox("排序方式", ["总发奖金", "平均完成率", "月度奖金"], key="okr_sort")
    ascending = st.checkbox("升序", value=False, key="okr_asc")
    
    display_df = summary.sort_values(sort_by, ascending=ascending)
    
    # 颜色标记
    def color_completion(val):
        if isinstance(val, (int, float)):
            if val >= 1.0:
                return 'background-color: #d1fae5; color: #065f46'
            elif val >= 0.7:
                return 'background-color: #fef3c7; color: #92400e'
            else:
                return 'background-color: #fee2e2; color: #991b1b'
        return ''
    
    styled = display_df[['顾问', '中文名', '级别', '团队', '指标数', '平均完成率', '月度奖金', '上月补发', '总发奖金']].style.map(
        color_completion, subset=['平均完成率']
    )
    
    st.dataframe(styled, use_container_width=True, hide_index=True)


def render_okr_detail(okr_loader: OKRDataLoader):
    """渲染OKR指标明细"""
    detail = okr_loader.to_dataframe()
    
    if detail.empty:
        st.warning("暂无OKR明细数据")
        return
    
    # 筛选
    st.markdown("#### 🔍 筛选")
    
    col1, col2 = st.columns(2)
    with col1:
        consultants = detail['顾问'].unique().tolist()
        selected = st.multiselect("选择顾问", consultants)
    with col2:
        projects = detail['考核项目'].unique().tolist()
        selected_projects = st.multiselect("考核项目", projects)
    
    filtered = detail.copy()
    if selected:
        filtered = filtered[filtered['顾问'].isin(selected)]
    if selected_projects:
        filtered = filtered[filtered['考核项目'].isin(selected_projects)]
    
    # 显示明细
    st.markdown("#### 📋 指标明细")
    
    display_cols = ['顾问', '考核项目', '考核指标', '权重', '实际完成', '实得奖金', '完成率']
    display_df = filtered[display_cols].copy()
    display_df['完成率'] = display_df['完成率'].apply(lambda x: f"{x*100:.1f}%" if pd.notna(x) else '-')
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # 顾问展开详情
    st.markdown("#### 📊 顾问OKR详情")
    
    for okr in okr_loader.consultant_okrs:
        with st.expander(f"{okr.consultant_name} ({okr.chinese_name}) - 总奖金: {format_currency(okr.total_bonus)}"):
            # 指标表格
            ind_data = []
            for ind in okr.indicators:
                ind_data.append({
                    '考核项目': ind.name,
                    '考核指标': ind.target,
                    '权重': ind.weight,
                    '计算规则': ind.rule[:50] + '...' if len(ind.rule) > 50 else ind.rule,
                    '实际完成': ind.actual,
                    '实得奖金': ind.bonus,
                    '完成率': f"{ind.completion_rate*100:.1f}%" if ind.completion_rate > 0 else '-',
                })
            
            if ind_data:
                st.dataframe(pd.DataFrame(ind_data), use_container_width=True, hide_index=True)
            
            # 汇总信息
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("月度奖金", format_currency(okr.month_bonus))
            with col2:
                st.metric("上月补发", format_currency(okr.prev_month_adjustment))
            with col3:
                st.metric("总发奖金", format_currency(okr.total_bonus))


def render_okr_system_comparison(okr_loader: OKRDataLoader, year: int, month: int):
    """渲染系统数据对比"""
    st.markdown("#### 🔄 OKR目标 vs 系统实时数据")
    st.caption("将Excel中的OKR目标与数据库中的实际业务数据进行对比")
    
    # 检查数据库连接
    try:
        import db_config_manager
        from gllue_db_client import GllueDBClient
        
        if not db_config_manager.has_config():
            st.warning("请先配置数据库连接")
            return
        
        db_client = GllueDBClient(db_config_manager.get_gllue_db_config())
        analyzer = OKRAnalyzer(okr_loader)
        analyzer.set_db_client(db_client)
        
        # 获取对比数据
        compare_df = analyzer.compare_with_system(year, month)
        
        if compare_df.empty:
            st.warning("暂无对比数据")
            return
        
        # 筛选有系统数据的行
        has_data = compare_df[compare_df['系统实际完成'] > 0]
        
        if has_data.empty:
            st.info("暂无系统数据可对比（可能所选月份无数据）")
            return
        
        st.markdown(f"#### 📊 有系统数据的指标 ({len(has_data)}条)")
        
        # 显示对比表
        display_cols = ['顾问', '考核项目', '考核指标', '权重', 'OKR实际完成', '系统实际完成', '差异']
        display_df = has_data[display_cols].copy()
        
        # 颜色标记差异
        def color_diff(val):
            if isinstance(val, (int, float)):
                if val > 0:
                    return 'color: #059669; font-weight: bold'
                elif val < 0:
                    return 'color: #dc2626'
            return ''
        
        styled = display_df.style.map(color_diff, subset=['差异'])
        st.dataframe(styled, use_container_width=True, hide_index=True)
        
        # 按顾问汇总
        st.markdown("#### 👤 按顾问汇总")
        
        consultant_summary = compare_df.groupby('顾问').agg({
            '系统实际完成': 'sum',
            'OKR实际完成': 'sum',
            '差异': 'sum',
        }).reset_index()
        
        consultant_summary['系统完成率'] = compare_df.groupby('顾问').apply(
            lambda x: x[x['目标值'] > 0]['系统实际完成'].sum() / x[x['目标值'] > 0]['目标值'].sum() 
            if x[x['目标值'] > 0]['目标值'].sum() > 0 else 0
        ).values
        
        st.dataframe(consultant_summary, use_container_width=True, hide_index=True)
        
    except Exception as e:
        st.error(f"系统数据对比失败: {e}")
        import traceback
        with st.expander("查看错误详情"):
            st.code(traceback.format_exc())
