"""
预警系统页面模块
"""

import math
import streamlit as st
from alert_config import get_alert_config, AlertSender


def format_currency(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "¥0"
    if abs(value) >= 10000:
        return f"¥{value/10000:.1f}万"
    return f"¥{value:,.0f}"


def render_alert_system(analyzer):
    """渲染智能预警系统"""
    st.markdown('<div class="main-header">🔔 智能预警系统</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">自动监控经营风险，及时推送预警通知</div>', unsafe_allow_html=True)
    
    if not analyzer.positions:
        st.info("📊 请上传成单数据以启用预警系统")
        return
    
    # 设置当前实际现金余额（从session_state获取首页设置的值）
    cash_reserve = analyzer.config.get('cash_reserve', 1800000)
    # 优先使用首页设置的值，否则使用默认值
    default_balance = st.session_state.get('home_current_balance', cash_reserve)
    current_balance = st.number_input(
        "当前现金余额 (元)",
        value=int(default_balance),
        step=100000,
        help="已回款可能已消耗，请填入当前实际现金余额（如180万）",
        key="alert_current_balance"
    )
    
    # 获取所有预警
    all_alerts = analyzer.get_all_alerts(current_balance=current_balance)
    summary = analyzer.get_alert_summary(current_balance=current_balance)
    
    # 统计卡片
    st.markdown("#### 📊 预警统计")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🔴 紧急", summary['danger'])
    with col2:
        st.metric("🟡 警告", summary['warning'])
    with col3:
        st.metric("🔵 提示", summary['info'])
    with col4:
        st.metric("总计", summary['total'])
    
    st.markdown("---")
    
    # 预警详情
    tabs = st.tabs(["现金流预警", "回款催收", "顾问绩效", "邮件配置"])
    
    with tabs[0]:
        cashflow_alerts = all_alerts['cashflow']
        if cashflow_alerts:
            for alert in cashflow_alerts:
                color = "#ef4444" if alert['level'] == 'danger' else "#f59e0b"
                st.markdown(f"""
                <div style="background: white; border-left: 4px solid {color}; 
                            padding: 15px; margin: 10px 0; border-radius: 8px;">
                    <strong style="color: {color};">{alert['title']}</strong>
                    <p>{alert['message']}</p>
                    <p style="color: #6b7280; font-size: 0.9rem;">
                        💡 {alert['action']} | 👤 {alert['responsible']} | 📅 {alert['due_date']}
                    </p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ 现金流状况良好，暂无预警")
    
    with tabs[1]:
        collection_alerts = all_alerts['collection']
        if collection_alerts:
            for alert in collection_alerts:
                with st.expander(f"{alert['level_text']} {alert['title']}"):
                    st.write(f"**详情:** {alert['message']}")
                    st.write(f"**建议:** {alert['action']}")
                    st.write(f"**负责人:** {alert['responsible']}")
                    
                    if 'items' in alert and alert['items']:
                        st.write("**涉及职位:**")
                        for item in alert['items']:
                            days_text = f"逾期{abs(item['days'])}天" if item['days'] < 0 else f"{item['days']}天后"
                            st.write(f"- {item['client']} - {item['consultant']}: "
                                   f"{format_currency(item['amount'])} ({days_text})")
        else:
            st.success("✅ 回款正常，暂无催收预警")
    
    with tabs[2]:
        consultant_alerts = all_alerts['consultant']
        if consultant_alerts:
            for alert in consultant_alerts:
                color = "#ef4444" if alert['level'] == 'danger' else "#f59e0b" if alert['level'] == 'warning' else "#3b82f6"
                st.markdown(f"""
                <div style="background: white; border-left: 4px solid {color}; 
                            padding: 15px; margin: 10px 0; border-radius: 8px;">
                    <strong style="color: {color};">{alert['title']}</strong>
                    <p>{alert['message']}</p>
                    <p style="color: #6b7280; font-size: 0.9rem;">
                        {alert['action']} | 负责人: {alert['responsible']}
                    </p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ 顾问绩效正常，暂无预警")
    
    with tabs[3]:
        alert_config = get_alert_config()
        render_email_config(alert_config)


def render_email_config(alert_config):
    st.markdown("#### 邮件配置")
    
    server = st.text_input("SMTP服务器", alert_config.config.get('smtp_server', ''))
    port = st.number_input("端口", value=alert_config.config.get('smtp_port', 465))
    username = st.text_input("邮箱账号", alert_config.config.get('smtp_username', ''))
    password = st.text_input("密码", value=alert_config.config.get('smtp_password', ''), type="password")
    
    if st.button("保存"):
        alert_config.update_config({
            'smtp_server': server,
            'smtp_port': port,
            'smtp_username': username,
            'smtp_password': password,
        })
        st.success("已保存")
    
    if st.button("测试连接"):
        sender = AlertSender(alert_config)
        success, msg = sender.test_connection()
        st.success(msg) if success else st.error(msg)
