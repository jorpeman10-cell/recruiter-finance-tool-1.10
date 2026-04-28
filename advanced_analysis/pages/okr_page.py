"""
OKR分析和绩效工资计算页面
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os
import tempfile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from okr_analyzer import OKRDataStore, OKRCalculator, OKRParser


def format_currency(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "¥0"
    if abs(value) >= 10000:
        return f"¥{value/10000:.1f}万"
    return f"¥{value:,.0f}"


def render_okr_page():
    """渲染OKR分析页面"""
    st.markdown('<div class="main-header">🎯 OKR分析与绩效工资</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">从Excel提取OKR规则，自动从系统获取数据计算奖金</div>', unsafe_allow_html=True)
    
    # 初始化
    store = OKRDataStore()
    
    # 侧边栏
    with st.sidebar:
        st.markdown("### 📅 考核月份")
        year = st.selectbox("年份", [2025, 2026], index=1, key="okr_year")
        month = st.selectbox("月份", list(range(1, 13)), index=2, key="okr_month")
    
    # 标签页
    tab1, tab2 = st.tabs(["📋 规则配置与计算", "📊 计算结果"])
    
    with tab1:
        render_config_and_calc(store, year, month)
    
    with tab2:
        render_results(store, year, month)


def render_config_and_calc(store: OKRDataStore, year: int, month: int):
    """规则配置和计算"""
    
    # 上传Excel
    st.markdown("### 1️⃣ 上传OKR模板")
    uploaded = st.file_uploader("选择OKR Excel文件", type=['xlsx', 'xls'], key='okr_upload')
    
    if uploaded:
        if st.button("🔄 解析规则", type="primary"):
            with st.spinner("解析中..."):
                try:
                    # 保存临时文件
                    temp = os.path.join(tempfile.gettempdir(), f"okr_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx")
                    with open(temp, "wb") as f:
                        f.write(uploaded.getvalue())
                    
                    # 解析并保存
                    consultants = store.parse_and_save(temp)
                    st.success(f"✅ 已解析并保存 {len(consultants)} 位顾问的OKR规则")
                    
                    # 显示解析结果
                    for c in consultants[:3]:
                        with st.expander(f"{c.name} ({c.chinese_name}) - {len(c.rules)}个指标"):
                            for r in c.rules:
                                st.write(f"- **{r.name}**: 目标={r.target_desc}, 权重={r.weight}, 周期={r.period}")
                                if r.score_rules:
                                    st.caption(f"  计分: {r.score_rules}")
                                if r.threshold_full_bonus > 0:
                                    st.caption(f"  门槛: {r.threshold_no_bonus}分无奖 / {r.threshold_half_bonus}分半奖 / {r.threshold_full_bonus}分全奖")
                    
                except Exception as e:
                    st.error(f"解析失败: {e}")
                    import traceback
                    st.code(traceback.format_exc())
    
    # 显示已配置规则
    st.markdown("---")
    st.markdown("### 2️⃣ 已配置的规则")
    
    configs = store.load_all()
    if not configs:
        st.info("暂无配置，请先上传OKR Excel模板")
        return
    
    st.write(f"共 {len(configs)} 位顾问已配置")
    
    # 选择顾问查看
    names = [c.name for c in configs]
    selected = st.selectbox("查看顾问规则", names)
    
    if selected:
        c = store.load(selected)
        if c:
            st.write(f"**级别**: {c.level} | **团队**: {c.team} | **汇报线**: {c.manager}")
            st.write(f"**奖金基数**: {c.base_bonus}元")
            
            rules_data = []
            for r in c.rules:
                rules_data.append({
                    '指标': r.name,
                    '目标': r.target_desc,
                    '权重': r.weight,
                    '周期': r.period,
                    '奖金基数': r.base_amount,
                    '计分规则': str(r.score_rules) if r.score_rules else '按比例',
                })
            st.dataframe(pd.DataFrame(rules_data), hide_index=True, use_container_width=True)
    
    # 自动计算
    st.markdown("---")
    st.markdown("### 3️⃣ 自动计算奖金")
    
    if not configs:
        st.warning("请先配置OKR规则")
        return
    
    # 检查数据库连接
    db_ok = False
    try:
        import db_config_manager
        from gllue_db_client import GllueDBClient
        db_ok = db_config_manager.has_config()
    except:
        pass
    
    if not db_ok:
        st.warning("⚠️ 未配置数据库连接，无法自动获取系统数据")
        return
    
    if st.button("🚀 开始计算", type="primary"):
        with st.spinner("计算中..."):
            try:
                db_client = GllueDBClient(db_config_manager.get_gllue_db_config())
                calc = OKRCalculator(db_client)
                
                all_results = []
                for c in configs:
                    result = calc.calculate(c, year, month)
                    all_results.append(result)
                
                # 保存到session_state
                st.session_state.okr_results = all_results
                st.success(f"✅ 计算完成！{len(all_results)}位顾问")
                
            except Exception as e:
                st.error(f"计算失败: {e}")
                import traceback
                st.code(traceback.format_exc())


def render_results(store: OKRDataStore, year: int, month: int):
    """显示计算结果"""
    
    if 'okr_results' not in st.session_state:
        st.info("请先前往『规则配置与计算』标签页进行计算")
        return
    
    results = st.session_state.okr_results
    
    # 汇总
    st.markdown("### 📊 汇总")
    total = sum(r['total_bonus'] for r in results)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("顾问人数", len(results))
    with c2:
        st.metric("总奖金", format_currency(total))
    with c3:
        avg = total / len(results) if results else 0
        st.metric("人均奖金", format_currency(avg))
    
    # 结果表格
    st.markdown("### 📋 明细")
    
    data = []
    for r in results:
        data.append({
            '顾问': r['consultant'],
            '中文名': r['chinese_name'],
            '总奖金': r['total_bonus'],
        })
    
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # 详细展开
    st.markdown("### 🔍 详细计算过程")
    for r in results:
        with st.expander(f"{r['consultant']} ({r['chinese_name']}) - {format_currency(r['total_bonus'])}"):
            for rule in r['rules']:
                col1, col2, col3 = st.columns([3, 2, 3])
                with col1:
                    st.write(f"**{rule['name']}**")
                    st.caption(f"目标: {rule['target']} | 权重: {rule['weight']}")
                with col2:
                    st.write(f"实际: {rule['actual']}")
                    st.write(f"奖金: {format_currency(rule['bonus'])}")
                with col3:
                    st.caption(rule['detail'])
