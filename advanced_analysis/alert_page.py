"""
预警系统页面模块
"""

import streamlit as st
from alert_config import get_alert_config, AlertSender


def format_currency(value):
    if value >= 10000:
        return f"¥{value/10000:.1f}万"
    return f"¥{value:,.0f}"


def render_alert_system(analyzer):
    st.markdown('<div class="main-header">智能预警系统</div>', unsafe_allow_html=True)
    
    if not analyzer.positions:
        st.info("请上传成单数据以启用预警系统")
        return
    
    alert_config = get_alert_config()
    all_alerts = analyzer.get_all_alerts()
    summary = analyzer.get_alert_summary()
    
    # 统计
    cols = st.columns(4)
    cols[0].metric("紧急", summary['danger'])
    cols[1].metric("警告", summary['warning'])
    cols[2].metric("提示", summary['info'])
    cols[3].metric("总计", summary['total'])
    
    # 详情
    tabs = st.tabs(["现金流", "回款", "顾问", "邮件配置"])
    
    with tabs[0]:
        for alert in all_alerts['cashflow']:
            color = "red" if alert['level'] == 'danger' else "orange"
            st.markdown(f"**{alert['title']}**")
            st.write(alert['message'])
            st.caption(f"建议: {alert['action']}")
    
    with tabs[1]:
        for alert in all_alerts['collection']:
            st.markdown(f"**{alert['title']}**")
            st.write(alert['message'])
    
    with tabs[2]:
        for alert in all_alerts['consultant']:
            st.markdown(f"**{alert['title']}**")
            st.write(alert['message'])
    
    with tabs[3]:
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
