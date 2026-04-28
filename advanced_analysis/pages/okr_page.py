"""
OKR分析和绩效工资计算页面
支持：规则配置、自动计算、人工校对
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from okr_analyzer import (
    OKRConfigManager, OKRCalculator, OKRResultStore,
    ConsultantOKRConfig, OKRRule, OKRResult
)


def format_currency(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "¥0"
    if abs(value) >= 10000:
        return f"¥{value/10000:.1f}万"
    return f"¥{value:,.0f}"


def render_okr_page():
    """渲染OKR分析页面"""
    st.markdown('<div class="main-header">🎯 OKR分析与绩效工资</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">自动计算OKR奖金，支持人工校对</div>', unsafe_allow_html=True)
    
    # 初始化配置管理器
    config_manager = OKRConfigManager()
    result_store = OKRResultStore()
    
    # 侧边栏：月份选择
    with st.sidebar:
        st.markdown("### 📅 考核月份")
        year = st.selectbox("年份", [2025, 2026], index=1, key="okr_year")
        month = st.selectbox("月份", list(range(1, 13)), index=2, key="okr_month")
    
    # 主内容区标签页
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 规则配置",
        "🤖 自动计算",
        "✏️ 人工校对",
        "📊 历史记录",
    ])
    
    with tab1:
        render_rule_config(config_manager)
    
    with tab2:
        render_auto_calculation(config_manager, result_store, year, month)
    
    with tab3:
        render_manual_review(result_store, year, month)
    
    with tab4:
        render_history(result_store)


def render_rule_config(config_manager: OKRConfigManager):
    """渲染规则配置页面"""
    st.markdown("### 📋 OKR规则配置")
    st.caption("上传Excel模板或手动配置每个顾问的OKR考核规则")
    
    # 上传Excel模板
    uploaded_file = st.file_uploader("上传OKR模板 (Excel)", type=['xlsx', 'xls'], key='okr_template')
    
    if uploaded_file:
        if st.button("🔄 解析并保存规则", type="primary"):
            with st.spinner("解析中..."):
                try:
                    # 保存临时文件
                    temp_path = f"/tmp/okr_template_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getvalue())
                    
                    # 解析规则
                    configs = config_manager.parse_from_excel(temp_path)
                    
                    st.success(f"✅ 成功解析并保存 {len(configs)} 位顾问的OKR规则")
                    
                    # 显示解析结果
                    for config in configs:
                        with st.expander(f"{config.consultant_name} ({config.chinese_name}) - {len(config.rules)}个指标"):
                            rules_data = []
                            for rule in config.rules:
                                rules_data.append({
                                    '指标类型': rule.indicator_type,
                                    '指标名称': rule.indicator_name,
                                    '目标值': rule.target_value,
                                    '权重': rule.weight,
                                    '奖金池': rule.bonus_pool,
                                    '周期': rule.period,
                                    '自动计算': '✅' if rule.is_auto_calculable else '❌',
                                })
                            st.dataframe(pd.DataFrame(rules_data), hide_index=True, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"解析失败: {e}")
    
    # 显示已配置规则
    st.markdown("---")
    st.markdown("### 📁 已配置的规则")
    
    configs = config_manager.load_all_configs()
    if not configs:
        st.info("暂无配置，请上传Excel模板")
        return
    
    st.write(f"共 {len(configs)} 位顾问已配置")
    
    # 顾问选择
    consultant_names = [c.consultant_name for c in configs]
    selected = st.selectbox("选择顾问查看/编辑规则", consultant_names)
    
    if selected:
        config = config_manager.load_config(selected)
        if config:
            with st.expander(f"{config.consultant_name} 的规则详情", expanded=True):
                st.write(f"**级别**: {config.level}")
                st.write(f"**团队**: {config.team}")
                st.write(f"**汇报线**: {config.manager}")
                st.write(f"**奖金基数**: {config.base_bonus}元")
                
                # 规则表格
                rules_df = pd.DataFrame([
                    {
                        '指标类型': r.indicator_type,
                        '指标名称': r.indicator_name,
                        '目标值': r.target_value,
                        '权重': r.weight,
                        '奖金池': r.bonus_pool,
                        '低门槛': r.threshold_low,
                        '中门槛': r.threshold_mid,
                        '全奖门槛': r.threshold_full,
                        '周期': r.period,
                    }
                    for r in config.rules
                ])
                st.dataframe(rules_df, hide_index=True, use_container_width=True)


def render_auto_calculation(config_manager: OKRConfigManager, result_store: OKRResultStore, year: int, month: int):
    """渲染自动计算页面"""
    st.markdown("### 🤖 自动计算OKR奖金")
    st.caption(f"计算月份: {year}年{month}月")
    
    # 检查数据库连接
    try:
        import db_config_manager
        from gllue_db_client import GllueDBClient
        
        if not db_config_manager.has_config():
            st.warning("⚠️ 未配置数据库连接，无法自动获取系统数据")
            db_client = None
        else:
            db_client = GllueDBClient(db_config_manager.get_gllue_db_config())
    except Exception as e:
        st.warning(f"⚠️ 数据库连接失败: {e}")
        db_client = None
    
    # 加载配置
    configs = config_manager.load_all_configs()
    if not configs:
        st.error("❌ 尚未配置OKR规则，请先前往『规则配置』标签页上传模板")
        return
    
    st.write(f"已加载 {len(configs)} 位顾问的OKR规则")
    
    # 计算按钮
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🚀 开始自动计算", type="primary"):
            with st.spinner("计算中..."):
                try:
                    calculator = OKRCalculator(db_client)
                    results = calculator.calculate_all(configs, year, month)
                    
                    # 保存结果
                    for result in results:
                        result_store.save_result(result)
                    
                    st.session_state.okr_calculation_results = results
                    st.success(f"✅ 计算完成！已保存 {len(results)} 位顾问的结果")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"计算失败: {e}")
                    import traceback
                    with st.expander("查看错误详情"):
                        st.code(traceback.format_exc())
    
    with col2:
        # 显示上次计算时间
        if 'okr_calculation_results' in st.session_state:
            st.caption("上次计算结果已加载")
    
    # 显示计算结果
    if 'okr_calculation_results' in st.session_state:
        results = st.session_state.okr_calculation_results
        
        st.markdown("---")
        st.markdown("### 📊 计算结果")
        
        # 汇总卡片
        total_bonus = sum(r.total_bonus for r in results)
        total_final = sum(r.final_bonus for r in results)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("计算奖金总额", format_currency(total_bonus))
        with c2:
            st.metric("最终应发总额", format_currency(total_final))
        with c3:
            confirmed = sum(1 for r in results if r.status == 'confirmed')
            st.metric("已确认", f"{confirmed}/{len(results)}人")
        
        # 结果表格
        result_data = []
        for r in results:
            result_data.append({
                '顾问': r.consultant_name,
                '中文名': r.chinese_name,
                '计算奖金': r.total_bonus,
                '上月补发': r.prev_month_adjustment,
                '最终应发': r.final_bonus,
                '状态': r.status,
            })
        
        result_df = pd.DataFrame(result_data)
        
        # 颜色标记
        def color_status(val):
            if val == 'confirmed':
                return 'background-color: #d1fae5; color: #065f46'
            elif val == 'adjusted':
                return 'background-color: #fef3c7; color: #92400e'
            return ''
        
        styled = result_df.style.map(color_status, subset=['状态'])
        st.dataframe(styled, use_container_width=True, hide_index=True)
        
        # 展开查看详情
        st.markdown("#### 📋 详细计算过程")
        for r in results:
            with st.expander(f"{r.consultant_name} ({r.chinese_name}) - 应发: {format_currency(r.final_bonus)}"):
                for ind in r.indicator_results:
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 3])
                    with col1:
                        st.write(f"**{ind['indicator_name']}**")
                        st.caption(f"类型: {ind['indicator_type']}")
                    with col2:
                        st.write(f"目标: {ind['target_value']}")
                        st.write(f"实际: {ind['actual_value']}")
                    with col3:
                        completion = ind['completion_rate']
                        st.write(f"完成率: {completion*100:.1f}%")
                        st.write(f"奖金: {format_currency(ind['calculated_bonus'])}")
                    with col4:
                        st.caption(ind['calculation_detail'])
                        if not ind['is_auto']:
                            st.warning("⚠️ 自定义指标，需人工核对")


def render_manual_review(result_store: OKRResultStore, year: int, month: int):
    """渲染人工校对页面"""
    st.markdown("### ✏️ 人工校对")
    st.caption("查看自动计算结果，进行人工调整和确认")
    
    # 加载该月的计算结果
    results = result_store.load_month_results(year, month)
    
    if not results:
        st.info("暂无计算结果，请先前往『自动计算』标签页进行计算")
        return
    
    # 顾问选择
    consultant_names = [r.consultant_name for r in results]
    selected = st.selectbox("选择顾问进行校对", consultant_names)
    
    if selected:
        result = next((r for r in results if r.consultant_name == selected), None)
        if not result:
            st.error("未找到该顾问的计算结果")
            return
        
        st.markdown(f"#### {result.consultant_name} ({result.chinese_name})")
        
        # 显示各项指标
        st.markdown("**指标明细**")
        for i, ind in enumerate(result.indicator_results):
            col1, col2, col3 = st.columns([3, 2, 2])
            with col1:
                st.write(f"{ind['indicator_name']}")
            with col2:
                st.write(f"实际: {ind['actual_value']} / 目标: {ind['target_value']}")
            with col3:
                st.write(f"奖金: {format_currency(ind['calculated_bonus'])}")
        
        st.markdown("---")
        
        # 调整区域
        st.markdown("**奖金调整**")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("计算奖金", format_currency(result.total_bonus))
        with col2:
            st.metric("上月补发", format_currency(result.prev_month_adjustment))
        with col3:
            st.metric("当前最终应发", format_currency(result.final_bonus))
        
        # 调整表单
        with st.form("adjust_form"):
            new_bonus = st.number_input(
                "调整后最终应发",
                value=float(result.final_bonus),
                step=100.0,
                min_value=0.0
            )
            adjust_note = st.text_area("调整说明", value=result.adjustment_note)
            
            col1, col2 = st.columns(2)
            with col1:
                confirm_btn = st.form_submit_button("✅ 确认无误", type="primary")
            with col2:
                adjust_btn = st.form_submit_button("✏️ 保存调整")
        
        if confirm_btn:
            result_store.confirm_result(
                result.consultant_name, year, month,
                adjusted_by="system", note="人工确认"
            )
            st.success("✅ 已确认")
            st.rerun()
        
        if adjust_btn:
            result_store.adjust_bonus(
                result.consultant_name, year, month,
                new_bonus=new_bonus,
                adjusted_by="admin",
                note=adjust_note
            )
            st.success("✅ 调整已保存")
            st.rerun()


def render_history(result_store: OKRResultStore):
    """渲染历史记录页面"""
    st.markdown("### 📊 历史记录")
    st.caption("查看历史月份的OKR计算结果")
    
    # 获取所有历史月份
    all_results = []
    for path in result_store.RESULT_DIR.glob("*.json"):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            all_results.append(data)
    
    if not all_results:
        st.info("暂无历史记录")
        return
    
    # 按月份分组
    months = sorted(set(f"{r['year']}-{r['month']:02d}" for r in all_results))
    
    selected_month = st.selectbox("选择月份", months)
    
    if selected_month:
        year, month = map(int, selected_month.split('-'))
        results = result_store.load_month_results(year, month)
        
        # 汇总
        st.markdown(f"#### {year}年{month}月 汇总")
        
        total = sum(r.final_bonus for r in results)
        confirmed = sum(1 for r in results if r.status == 'confirmed')
        adjusted = sum(1 for r in results if r.status == 'adjusted')
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("总人数", len(results))
        with c2:
            st.metric("应发总额", format_currency(total))
        with c3:
            st.metric("确认状态", f"已确认:{confirmed} / 已调整:{adjusted}")
        
        # 明细表
        history_data = []
        for r in results:
            history_data.append({
                '顾问': r.consultant_name,
                '中文名': r.chinese_name,
                '计算奖金': r.total_bonus,
                '上月补发': r.prev_month_adjustment,
                '最终应发': r.final_bonus,
                '状态': r.status,
                '调整人': r.adjusted_by,
                '调整说明': r.adjustment_note,
            })
        
        st.dataframe(pd.DataFrame(history_data), use_container_width=True, hide_index=True)
