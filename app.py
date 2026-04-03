"""
猎头公司财务分析工具 - Streamlit Web应用
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os
import sys

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models import RecruitmentFinanceAnalyzer, create_sample_data

# 页面配置
st.set_page_config(
    page_title="猎头公司财务分析工具",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E3A8A;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #F3F4F6;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1E40AF;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #6B7280;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #1E3A8A;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #E5E7EB;
        padding-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# 初始化session state
if 'analyzer' not in st.session_state:
    st.session_state.analyzer = RecruitmentFinanceAnalyzer()
    st.session_state.consultants_df = None
    st.session_state.deals_df = None
    st.session_state.expenses_df = None


def format_currency(value):
    """格式化货币"""
    # 处理 None、NaN 或空值
    if value is None or (isinstance(value, float) and (value != value)):  # NaN 检查
        return "¥0"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "¥0"
    
    if value >= 1000000:
        return f"¥{value/1000000:.2f}M"
    elif value >= 1000:
        return f"¥{value/1000:.1f}K"
    else:
        return f"¥{value:.0f}"


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.title("💼 猎头财务分析")
        
        st.markdown("---")
        
        # 数据管理
        st.subheader("📊 数据管理")
        
        # 数据操作按钮
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 示例数据", use_container_width=True):
                consultants_df, deals_df, expenses_df = create_sample_data()
                st.session_state.analyzer = RecruitmentFinanceAnalyzer()
                st.session_state.analyzer.load_from_dataframes(deals_df, consultants_df, expenses_df)
                st.session_state.consultants_df = consultants_df
                st.session_state.deals_df = deals_df
                st.session_state.expenses_df = expenses_df
                st.success("已加载示例数据！")
                st.rerun()
        with col2:
            if st.button("🗑️ 清空数据", use_container_width=True):
                st.session_state.analyzer = RecruitmentFinanceAnalyzer()
                st.session_state.consultants_df = None
                st.session_state.deals_df = None
                st.session_state.expenses_df = None
                st.success("已清空所有数据！")
                st.rerun()
        
        st.markdown("---")
        
        # 数据上传
        st.subheader("📁 上传数据")
        
        uploaded_deals = st.file_uploader("上传成单数据 (Excel/CSV)", 
                                          type=['xlsx', 'csv'],
                                          key='deals_upload')
        uploaded_consultants = st.file_uploader("上传顾问数据 (可选)", 
                                                type=['xlsx', 'csv'],
                                                key='consultants_upload')
        # 根据当前模式提示是否需要上传费用数据
        if st.session_state.get('analysis_mode') == '内部':
            st.caption("💡 内部核算版本不需要费用数据，成本通过顾问基本月薪自动计算")
            uploaded_expenses = None
        else:
            uploaded_expenses = st.file_uploader("上传费用数据 (可选)", 
                                                 type=['xlsx', 'csv'],
                                                 key='expenses_upload')
        
        # 预测数据上传
        uploaded_forecasts = st.file_uploader("上传预测/在途单数据 (可选)", 
                                              type=['xlsx', 'csv'],
                                              key='forecasts_upload')
        if uploaded_forecasts:
            st.caption("💡 预测数据用于分析在途单和预测未来收入")
        
        # 只要有任意数据上传，就显示加载按钮
        has_upload = (uploaded_deals is not None or 
                      uploaded_consultants is not None or 
                      uploaded_expenses is not None or
                      uploaded_forecasts is not None)
        
        if has_upload:
            st.info(f"📎 已选择文件:\n" + 
                    (f"- 成单数据\n" if uploaded_deals else "") +
                    (f"- 顾问数据\n" if uploaded_consultants else "") +
                    (f"- 费用数据\n" if uploaded_expenses else "") +
                    (f"- 预测数据" if uploaded_forecasts else ""))
            
            if st.button("📥 加载上传的数据", use_container_width=True):
                try:
                    # 读取成单数据（如果上传了）
                    if uploaded_deals:
                        if uploaded_deals.name.endswith('.csv'):
                            deals_df = pd.read_csv(uploaded_deals, comment='#')
                        else:
                            deals_df = pd.read_excel(uploaded_deals)
                        st.session_state.deals_df = deals_df
                    else:
                        deals_df = st.session_state.get('deals_df', None)
                    
                    # 读取顾问数据（如果上传了）
                    if uploaded_consultants:
                        if uploaded_consultants.name.endswith('.csv'):
                            consultants_df = pd.read_csv(uploaded_consultants, comment='#')
                        else:
                            consultants_df = pd.read_excel(uploaded_consultants)
                        st.session_state.consultants_df = consultants_df
                    else:
                        consultants_df = st.session_state.get('consultants_df', None)
                    
                    # 读取费用数据（如果上传了）
                    if uploaded_expenses:
                        if uploaded_expenses.name.endswith('.csv'):
                            expenses_df = pd.read_csv(uploaded_expenses, comment='#')
                        else:
                            expenses_df = pd.read_excel(uploaded_expenses)
                        st.session_state.expenses_df = expenses_df
                    else:
                        expenses_df = st.session_state.get('expenses_df', None)
                    
                    # 读取预测数据（如果上传了）
                    if uploaded_forecasts:
                        if uploaded_forecasts.name.endswith('.csv'):
                            forecasts_df = pd.read_csv(uploaded_forecasts, comment='#')
                        else:
                            forecasts_df = pd.read_excel(uploaded_forecasts)
                        st.session_state.forecasts_df = forecasts_df
                    else:
                        forecasts_df = st.session_state.get('forecasts_df', None)
                    
                    # 更新分析器
                    st.session_state.analyzer = RecruitmentFinanceAnalyzer()
                    st.session_state.analyzer.load_from_dataframes(deals_df, consultants_df, expenses_df)
                    
                    # 加载预测数据
                    if forecasts_df is not None:
                        st.session_state.analyzer.load_forecasts_from_dataframe(forecasts_df)
                    
                    # 验证数据加载
                    analyzer = st.session_state.analyzer
                    if len(analyzer.deals) == 0:
                        st.warning("⚠️ 没有加载到成单数据，请检查文件格式")
                    else:
                        # 显示第一条数据作为验证
                        first_deal = analyzer.deals[0]
                        st.success(f"✅ 成功加载 {len(analyzer.deals)} 条成单数据")
                        with st.expander("查看第一条数据详情"):
                            st.write({
                                "成单编号": first_deal.deal_id,
                                "客户": first_deal.client_name,
                                "佣金": first_deal.fee_amount,
                                "实际回款": first_deal.actual_payment,
                                "上年遗留回款": first_deal.prior_year_collection
                            })
                    st.rerun()
                except Exception as e:
                    st.error(f"数据加载失败: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
        
        st.markdown("---")
        
        # Gllue API 同步功能
        st.subheader("🔄 Gllue API 同步")
        
        with st.expander("配置谷露 API 连接", expanded=False):
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
                placeholder="从谷露系统获取的 API Key",
                help="请联系谷露客服或管理员获取 API 密钥"
            )
            
            # 同步日期范围
            col1, col2 = st.columns(2)
            with col1:
                sync_start_date = st.date_input(
                    "开始日期",
                    value=datetime.now() - timedelta(days=365),
                    help="同步此日期之后的 Offer/入职数据"
                )
            with col2:
                sync_end_date = st.date_input(
                    "结束日期",
                    value=datetime.now(),
                    help="同步此日期之前的 Offer/入职数据"
                )
            
            # 保存配置
            if st.button("💾 保存配置", use_container_width=True):
                st.session_state.gllue_base_url = gllue_base_url
                st.session_state.gllue_api_key = gllue_api_key
                st.success("✅ 配置已保存")
            
            # 测试连接
            if st.button("🔌 测试连接", use_container_width=True):
                if not gllue_base_url or not gllue_api_key:
                    st.error("❌ 请先填写域名和 API 密钥")
                else:
                    with st.spinner("正在测试连接..."):
                        try:
                            # 导入 Gllue 客户端
                            from gllue_client import GllueConfig, GllueAPIClient
                            
                            config = GllueConfig(
                                base_url=gllue_base_url,
                                api_key=gllue_api_key
                            )
                            client = GllueAPIClient(config)
                            
                            # 尝试获取少量数据测试连接
                            test_data = client.get_users()
                            st.success(f"✅ 连接成功！获取到 {len(test_data)} 个用户")
                        except Exception as e:
                            st.error(f"❌ 连接失败: {str(e)}")
            
            # 执行同步
            if st.button("🚀 同步数据", type="primary", use_container_width=True):
                if not gllue_base_url or not gllue_api_key:
                    st.error("❌ 请先填写域名和 API 密钥")
                else:
                    with st.spinner("正在从 Gllue 同步数据..."):
                        try:
                            from gllue_client import GllueConfig, GllueAPIClient
                            
                            config = GllueConfig(
                                base_url=gllue_base_url,
                                api_key=gllue_api_key
                            )
                            client = GllueAPIClient(config)
                            
                            # 同步数据
                            stats = client.sync_to_finance_analyzer(
                                st.session_state.analyzer,
                                start_date=sync_start_date.strftime('%Y-%m-%d'),
                                end_date=sync_end_date.strftime('%Y-%m-%d')
                            )
                            
                            st.success(f"""
                            ✅ 同步完成！
                            - 获取 {stats['offers_fetched']} 条 Offer 数据
                            - 获取 {stats['onboards_fetched']} 条入职数据
                            - 导入 {stats['positions_added']} 条成单记录
                            """)
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ 同步失败: {str(e)}")
                            import traceback
                            st.error(traceback.format_exc())
        
        st.markdown("---")
        
        # 分析模式切换
        st.subheader("🔀 分析模式")
        
        # 初始化分析模式
        if 'analysis_mode' not in st.session_state:
            st.session_state.analysis_mode = '真实数据'
        
        analysis_mode = st.radio(
            "选择查看模式",
            options=['真实数据', '内部核算版本（给顾问展示）'],
            index=0 if st.session_state.analysis_mode == '真实数据' else 1,
            help="真实数据：包含真实运营成本\n内部核算版本：使用顾问基本月薪×3×1.2计算成本，用于给顾问展示的盈亏分析"
        )
        
        st.session_state.analysis_mode = '真实数据' if analysis_mode == '真实数据' else '内部'
        
        if st.session_state.analysis_mode == '内部':
            st.info("""
            📊 **内部核算规则：**
            - 顾问成本 = 基本月薪 × 3 × 1.2
            - 3倍包括：工资、社保公积金、奖金、增值税、营运成本
            - 1.2 = 20%利润目标
            """)
        
        st.caption("""
        💡 **数据格式提示：**
        - `actual_payment` = 总回款（已含上年遗留）
        - `prior_year_collection` = 上年遗留部分（仅明细标注）
        - 本年回款 = actual_payment - prior_year_collection
        """)
        
        # 显示已加载数据概览
        st.markdown("---")
        st.subheader("📊 数据概览")
        
        analyzer = st.session_state.analyzer
        if analyzer.deals:
            try:
                revenue = analyzer.get_revenue_summary()
                st.success(f"✅ 已加载 {len(analyzer.deals)} 条成单数据")
                
                # 显示收入统计
                st.write("**回款构成：**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("总回款", format_currency(revenue.get('total_collected', 0)))
                with col2:
                    st.metric("其中：本年回款", format_currency(revenue.get('current_year_collection', 0)))
                with col3:
                    st.metric("其中：上年遗留", format_currency(revenue.get('prior_year_collection', 0)))
                
                st.write(f"**总佣金：** {format_currency(revenue.get('total_fee', 0))}")
                
                if revenue.get('prior_year_collection', 0) == 0:
                    st.info("💡 没有上年遗留回款数据")
            except Exception as e:
                st.error(f"计算收入概览时出错: {e}")
        else:
            st.warning("⚠️ 暂无成单数据，请上传数据文件")
        
        if analyzer.consultants:
            st.write(f"👥 顾问数: {len(analyzer.consultants)} 人")
        
        if analyzer.expenses:
            total_expense = sum(e.amount or 0 for e in analyzer.expenses)
            st.write(f"💰 费用记录: {len(analyzer.expenses)} 条，合计 {format_currency(total_expense)}")
        
        if analyzer.forecasts:
            forecast_summary = analyzer.get_forecast_summary()
            st.write(f"📈 预测数据: {len(analyzer.forecasts)} 条在途单")
            st.write(f"   • 预计佣金总额: {format_currency(forecast_summary.get('total_estimated_fee', 0))}")
            st.write(f"   • 加权预测收入: {format_currency(forecast_summary.get('weighted_revenue', 0))}")
            st.write(f"   • 平均成功率: {forecast_summary.get('avg_success_rate', 0):.1f}%")
        
        st.markdown("---")
        
        # 导出报告
        st.subheader("📄 导出报告")
        if st.button("📥 下载Excel报告", use_container_width=True):
            try:
                report_path = "财务分析报告.xlsx"
                st.session_state.analyzer.export_report(report_path)
                with open(report_path, "rb") as f:
                    st.download_button(
                        label="点击下载",
                        data=f,
                        file_name="猎头公司财务分析报告.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            except Exception as e:
                st.error(f"报告导出失败: {str(e)}")
        
        st.markdown("---")
        st.caption("© 2024 猎头财务分析工具 v1.0")


def render_overview():
    """渲染总览仪表板"""
    # 判断当前模式
    is_internal_mode = st.session_state.get('analysis_mode') == '内部'
    
    if is_internal_mode:
        st.markdown('<div class="main-header">📊 盈亏分析看板（内部核算版本）</div>', unsafe_allow_html=True)
        st.info("📌 此版本使用内部核算成本（顾问基本月薪×3×1.2），用于给顾问展示的盈亏分析")
    else:
        st.markdown('<div class="main-header">📊 财务总览仪表板</div>', unsafe_allow_html=True)
    
    analyzer = st.session_state.analyzer
    
    # 根据模式获取数据
    revenue = analyzer.get_revenue_summary()
    
    if is_internal_mode:
        expense = analyzer.get_internal_expense_summary()
        profit = analyzer.get_internal_profit_analysis()
    else:
        expense = analyzer.get_expense_summary()
        profit = analyzer.get_profit_analysis()
    
    # 调试信息（开发时使用，可删除）
    # st.write("调试 - 收入汇总:", revenue)
    # st.write("调试 - 利润:", profit)
    # st.write("调试 - 成单数:", len(analyzer.deals))
    # if analyzer.deals:
    #     st.write("调试 - 第一条成单:", {
    #         "deal_id": analyzer.deals[0].deal_id,
    #         "fee_amount": analyzer.deals[0].fee_amount,
    #         "actual_payment": analyzer.deals[0].actual_payment,
    #         "prior_year_collection": analyzer.deals[0].prior_year_collection
    #     })
    
    kpi = analyzer.get_kpi_dashboard()
    
    # 关键指标卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{format_currency(revenue['total_fee'])}</div>
            <div class="metric-label">总佣金收入</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{format_currency(revenue['total_collected'])}</div>
            <div class="metric-label">总回款（含上年遗留）</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # 显示上年遗留回款（如果有）
        prior_year = revenue.get('prior_year_collection') or 0
        if prior_year > 0:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{format_currency(prior_year)}</div>
                <div class="metric-label">其中：上年遗留回款</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            cost_label = "核算成本" if is_internal_mode else "总成本"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{format_currency(expense.get('total_expense', 0))}</div>
                <div class="metric-label">{cost_label}</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col4:
        # 显示本年回款（总回款 - 上年遗留）
        current_year = revenue.get('current_year_collection') or 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #3B82F6;">{format_currency(current_year)}</div>
            <div class="metric-label">其中：本年回款</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 第二行指标
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{revenue['total_deals']}</div>
            <div class="metric-label">成单总数</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{format_currency(revenue['avg_deal_size'])}</div>
            <div class="metric-label">平均单值</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{revenue['collection_rate']:.1f}%</div>
            <div class="metric-label">回款率</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{kpi['avg_collection_days']:.0f}天</div>
            <div class="metric-label">平均回款周期</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 月度趋势图表
    st.markdown('<div class="section-header">📈 月度趋势分析</div>', unsafe_allow_html=True)
    
    monthly_revenue = analyzer.get_monthly_revenue()
    monthly_profit = analyzer.get_monthly_profit()
    
    if not monthly_revenue.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # 收入趋势
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=monthly_revenue['月份'],
                y=monthly_revenue['佣金金额'],
                name='佣金金额',
                marker_color='#3B82F6'
            ))
            # 本年回款
            fig.add_trace(go.Bar(
                x=monthly_revenue['月份'],
                y=monthly_revenue['本年回款'],
                name='本年回款',
                marker_color='#10B981'
            ))
            # 如果有上年遗留回款数据，添加显示
            if '上年遗留回款' in monthly_revenue.columns and monthly_revenue['上年遗留回款'].sum() > 0:
                fig.add_trace(go.Bar(
                    x=monthly_revenue['月份'],
                    y=monthly_revenue['上年遗留回款'],
                    name='上年遗留回款',
                    marker_color='#F59E0B'
                ))
            # 总回款（本年+上年）
            fig.add_trace(go.Scatter(
                x=monthly_revenue['月份'],
                y=monthly_revenue['回款金额'],
                name='总回款',
                mode='lines+markers',
                line=dict(color='#EF4444', width=3)
            ))
            fig.update_layout(
                title='月度收入趋势',
                xaxis_title='月份',
                yaxis_title='金额 (元)',
                height=350,
                template='plotly_white',
                barmode='group',
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 成单数趋势
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=monthly_revenue['月份'],
                y=monthly_revenue['成单数'],
                marker_color='#8B5CF6',
                text=monthly_revenue['成单数'],
                textposition='outside'
            ))
            fig.update_layout(
                title='月度成单数',
                xaxis_title='月份',
                yaxis_title='成单数',
                height=350,
                template='plotly_white',
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无月度数据")
    
    # 内部核算版本：显示成本明细
    if is_internal_mode and 'consultant_details' in profit and not profit['consultant_details'].empty:
        st.markdown("---")
        st.markdown('<div class="section-header">👥 顾问成本明细（内部核算）</div>', unsafe_allow_html=True)
        
        details_df = profit['consultant_details'].copy()
        
        # 格式化金额列
        display_df = details_df.copy()
        display_df['基本月薪'] = display_df['基本月薪'].apply(format_currency)
        display_df['月度成本'] = display_df['月度成本'].apply(format_currency)
        display_df['总成本'] = display_df['总成本'].apply(format_currency)
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # 显示核算公式说明
        st.caption(f"""
        💡 **核算公式**：顾问成本 = 基本月薪 × 3 × 1.2 × {profit.get('months', 3):.1f}个月  
        （3倍包括：工资、社保公积金、奖金、增值税、营运成本；1.2为20%利润目标）
        """)


def render_revenue_analysis():
    """渲染收入分析页面"""
    st.markdown('<div class="main-header">💰 收入分析</div>', unsafe_allow_html=True)
    
    analyzer = st.session_state.analyzer
    
    # 时间筛选
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", value=datetime.now() - timedelta(days=180))
    with col2:
        end_date = st.date_input("结束日期", value=datetime.now())
    
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    # 收入汇总
    revenue = analyzer.get_revenue_summary(start_dt, end_dt)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("成单总数", f"{revenue['total_deals']}单")
    col2.metric("佣金总额", format_currency(revenue['total_fee']))
    col3.metric("实际回款", format_currency(revenue['total_collected']))
    col4.metric("平均单值", format_currency(revenue['avg_deal_size']))
    
    st.markdown("---")
    
    # 顾问业绩排名
    st.markdown('<div class="section-header">🏆 顾问业绩排名</div>', unsafe_allow_html=True)
    
    consultant_performance = analyzer.get_revenue_by_consultant()
    if not consultant_performance.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 业绩柱状图
            fig = px.bar(
                consultant_performance,
                x='顾问',
                y=['佣金总额', '回款总额'],
                barmode='group',
                title='顾问业绩对比',
                template='plotly_white',
                color_discrete_sequence=['#3B82F6', '#10B981']
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 业绩表格
            display_df = consultant_performance.copy()
            display_df['佣金总额'] = display_df['佣金总额'].apply(format_currency)
            display_df['回款总额'] = display_df['回款总额'].apply(format_currency)
            display_df['平均单值'] = display_df['平均单值'].apply(format_currency)
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无顾问业绩数据")
    
    st.markdown("---")
    
    # 客户分析
    st.markdown('<div class="section-header">🏢 客户分析</div>', unsafe_allow_html=True)
    
    client_analysis = analyzer.get_revenue_by_client()
    if not client_analysis.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # 客户收入饼图（Top 10）
            top_clients = client_analysis.head(10)
            fig = px.pie(
                top_clients,
                values='佣金总额',
                names='客户',
                title='Top 10 客户收入占比',
                template='plotly_white'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 客户价值散点图
            # 检查是否有平均职位年薪数据，没有则使用默认大小
            if client_analysis['平均职位年薪'].isna().all():
                # 如果没有年薪数据，不使用 size 参数
                fig = px.scatter(
                    client_analysis,
                    x='成单数',
                    y='佣金总额',
                    color='客户',
                    title='客户价值分析（无年薪数据）',
                    template='plotly_white'
                )
            else:
                # 填充空值为0，避免报错
                plot_df = client_analysis.copy()
                plot_df['平均职位年薪'] = plot_df['平均职位年薪'].fillna(0)
                fig = px.scatter(
                    plot_df,
                    x='成单数',
                    y='佣金总额',
                    size='平均职位年薪',
                    color='客户',
                    title='客户价值分析（气泡大小=平均职位年薪）',
                    template='plotly_white',
                    size_max=50
                )
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无客户数据")


def render_cost_analysis():
    """渲染成本分析页面"""
    # 判断当前模式
    is_internal_mode = st.session_state.get('analysis_mode') == '内部'
    
    if is_internal_mode:
        st.markdown('<div class="main-header">📉 成本分析（内部核算版本）</div>', unsafe_allow_html=True)
        st.info("📌 此版本使用内部核算成本公式：顾问基本月薪 × 3 × 1.2")
    else:
        st.markdown('<div class="main-header">📉 成本分析</div>', unsafe_allow_html=True)
    
    analyzer = st.session_state.analyzer
    
    # 根据模式获取数据
    if is_internal_mode:
        # 内部核算版本：只显示顾问核算成本
        expense_summary = analyzer.get_internal_expense_summary()
        
        col1, col2 = st.columns(2)
        col1.metric("核算总成本", format_currency(expense_summary['total_expense']))
        col2.metric("顾问核算成本", format_currency(expense_summary['consultant_cost']))
        
        st.markdown("---")
        
        # 显示顾问成本明细
        st.markdown('<div class="section-header">👥 顾问成本明细（内部核算）</div>', unsafe_allow_html=True)
        
        if 'consultant_details' in expense_summary and not expense_summary['consultant_details'].empty:
            details_df = expense_summary['consultant_details'].copy()
            
            # 格式化金额列
            display_df = details_df.copy()
            display_df['基本月薪'] = display_df['基本月薪'].apply(format_currency)
            display_df['月度成本'] = display_df['月度成本'].apply(format_currency)
            display_df['总成本'] = display_df['总成本'].apply(format_currency)
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # 显示核算公式说明
            months = expense_summary.get('months', 3)
            st.caption(f"""
            💡 **核算公式**：顾问成本 = 基本月薪 × 3 × 1.2 × {months:.1f}个月  
            - 3倍包括：工资、社保公积金、奖金、增值税、营运成本（支持部门、房租、办公等）
            - 1.2 = 20%利润目标
            """)
        else:
            st.info("暂无顾问数据")
        
        return  # 内部核算版本到此结束，不显示真实费用相关的内容
    
    # 真实数据版本：显示完整成本分析
    expense_summary = analyzer.get_expense_summary()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("总成本", format_currency(expense_summary['total_expense']))
    col2.metric("运营成本", format_currency(expense_summary['operational_expense']))
    col3.metric("人力成本", format_currency(expense_summary['personnel_cost']))
    
    st.markdown("---")
    
    # 成本构成
    st.markdown('<div class="section-header">📊 成本构成分析</div>', unsafe_allow_html=True)
    
    expense_by_category = expense_summary['by_category']
    if not expense_by_category.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # 成本饼图
            fig = px.pie(
                expense_by_category,
                values='金额',
                names='类别',
                title='成本类别分布',
                template='plotly_white',
                hole=0.4
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 成本表格
            display_df = expense_by_category.copy()
            display_df['金额'] = display_df['金额'].apply(format_currency)
            display_df['占比'] = (expense_by_category['金额'] / expense_by_category['金额'].sum() * 100).round(1).astype(str) + '%'
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无费用数据，请上传费用数据以查看完整成本分析")
    
    st.markdown("---")
    
    # 按部门统计
    st.markdown('<div class="section-header">🏢 费用部门分布</div>', unsafe_allow_html=True)
    
    expense_by_dept = analyzer.get_expense_by_department()
    if not expense_by_dept.empty and len(expense_by_dept) > 1:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.pie(
                expense_by_dept,
                values='金额',
                names='部门',
                title='各部门费用占比',
                template='plotly_white'
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            display_df = expense_by_dept.copy()
            display_df['金额'] = display_df['金额'].apply(format_currency)
            display_df['占比'] = (expense_by_dept['金额'] / expense_by_dept['金额'].sum() * 100).round(1).astype(str) + '%'
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # 月度费用趋势
    st.markdown('<div class="section-header">📈 月度费用趋势</div>', unsafe_allow_html=True)
    
    monthly_expense = analyzer.get_monthly_expense()
    if not monthly_expense.empty:
        fig = px.bar(
            monthly_expense,
            x='月份',
            y='金额',
            title='月度费用支出',
            template='plotly_white',
            color='金额',
            color_continuous_scale='Reds'
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无月度费用数据，请上传费用数据")
    
    st.markdown("---")
    
    # 费用明细表
    st.markdown('<div class="section-header">📋 费用明细</div>', unsafe_allow_html=True)
    
    expense_detail = analyzer.get_expense_detail()
    if not expense_detail.empty:
        # 筛选
        col1, col2 = st.columns(2)
        with col1:
            filter_category = st.multiselect(
                "筛选费用类型", 
                options=expense_detail['费用类型'].unique(),
                key='expense_category_filter'
            )
        with col2:
            filter_dept = st.multiselect(
                "筛选部门", 
                options=[d for d in expense_detail['部门'].unique() if d != '-'],
                key='expense_dept_filter'
            )
        
        filtered_df = expense_detail.copy()
        if filter_category:
            filtered_df = filtered_df[filtered_df['费用类型'].isin(filter_category)]
        if filter_dept:
            filtered_df = filtered_df[filtered_df['部门'].isin(filter_dept)]
        
        # 格式化金额
        display_df = filtered_df.copy()
        display_df['金额'] = display_df['金额'].apply(format_currency)
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # 统计
        total_filtered = filtered_df['金额'].sum()
        st.markdown(f"**筛选总计:** {format_currency(total_filtered)} ({len(filtered_df)} 条记录)")
    else:
        st.info("暂无费用明细数据")


def render_profit_analysis():
    """渲染利润分析页面"""
    # 判断当前模式
    is_internal_mode = st.session_state.get('analysis_mode') == '内部'
    
    if is_internal_mode:
        st.markdown('<div class="main-header">💹 盈亏分析（内部核算版本）</div>', unsafe_allow_html=True)
        st.info("📌 此版本使用内部核算成本，用于给顾问展示的盈亏分析")
    else:
        st.markdown('<div class="main-header">💹 利润分析</div>', unsafe_allow_html=True)
    
    analyzer = st.session_state.analyzer
    
    # 根据模式获取数据
    if is_internal_mode:
        profit = analyzer.get_internal_profit_analysis()
    else:
        profit = analyzer.get_profit_analysis()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总佣金", format_currency(profit.get('total_revenue', 0)))
    col2.metric("总回款（含上年）", format_currency(profit.get('total_collected', 0)))
    
    # 显示上年遗留回款（如果有）
    prior_year = profit.get('prior_year_collection') or 0
    if prior_year > 0:
        col3.metric("其中：上年遗留", format_currency(prior_year))
    else:
        cost_label = "核算成本" if is_internal_mode else "总成本"
        col3.metric(cost_label, format_currency(profit.get('total_expense', 0)))
    
    # 显示本年回款和利润
    current_year = profit.get('current_year_collection') or 0
    col4.metric("其中：本年回款", format_currency(current_year))
    
    # 再添加一行显示成本和利润
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    cols = st.columns(4)
    cols[0].metric("总成本", format_currency(profit.get('total_expense', 0)))
    
    profit_label = "盈亏" if is_internal_mode else "毛利润"
    gross_profit = profit.get('gross_profit', 0)
    profit_margin = profit.get('profit_margin') or 0
    cols[1].metric(profit_label, format_currency(gross_profit), f"{profit_margin:.1f}%")
    
    st.markdown("---")
    
    # 月度利润趋势
    st.markdown('<div class="section-header">📈 月度利润趋势</div>', unsafe_allow_html=True)
    
    monthly_profit = analyzer.get_monthly_profit()
    if not monthly_profit.empty and '利润' in monthly_profit.columns:
        # 利润趋势图
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig.add_trace(
            go.Bar(
                x=monthly_profit['月份'],
                y=monthly_profit['回款金额'],
                name='回款金额',
                marker_color='#3B82F6'
            ),
            secondary_y=False
        )
        
        fig.add_trace(
            go.Bar(
                x=monthly_profit['月份'],
                y=monthly_profit['金额'],
                name='费用支出',
                marker_color='#EF4444'
            ),
            secondary_y=False
        )
        
        fig.add_trace(
            go.Scatter(
                x=monthly_profit['月份'],
                y=monthly_profit['利润'],
                name='利润',
                mode='lines+markers',
                line=dict(color='#10B981', width=3),
                marker=dict(size=10)
            ),
            secondary_y=True
        )
        
        fig.update_layout(
            title='月度利润分析',
            template='plotly_white',
            height=450,
            barmode='group',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        
        fig.update_yaxes(title_text="金额", secondary_y=False)
        fig.update_yaxes(title_text="利润", secondary_y=True)
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 利润率趋势
        fig2 = go.Figure()
        colors = ['#10B981' if p >= 0 else '#EF4444' for p in monthly_profit['利润率']]
        fig2.add_trace(go.Bar(
            x=monthly_profit['月份'],
            y=monthly_profit['利润率'],
            marker_color=colors,
            text=[f"{p:.1f}%" for p in monthly_profit['利润率']],
            textposition='outside'
        ))
        fig2.update_layout(
            title='月度利润率趋势',
            xaxis_title='月份',
            yaxis_title='利润率 (%)',
            template='plotly_white',
            height=350
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("暂无利润数据")
    
    st.markdown("---")
    
    # 顾问贡献利润
    st.markdown('<div class="section-header">👥 顾问贡献利润</div>', unsafe_allow_html=True)
    
    consultant_profit = analyzer.get_consultant_performance()
    if not consultant_profit.empty and '贡献利润' in consultant_profit.columns:
        # 贡献利润柱状图
        colors = ['#10B981' if p >= 0 else '#EF4444' for p in consultant_profit['贡献利润']]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=consultant_profit['顾问'],
            y=consultant_profit['贡献利润'],
            marker_color=colors,
            text=[format_currency(p) for p in consultant_profit['贡献利润']],
            textposition='outside'
        ))
        fig.update_layout(
            title='顾问贡献利润',
            xaxis_title='顾问',
            yaxis_title='贡献利润',
            template='plotly_white',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # KPI完成率
        fig2 = px.bar(
            consultant_profit,
            x='顾问',
            y='KPI完成率',
            title='顾问KPI完成率',
            template='plotly_white',
            color='KPI完成率',
            color_continuous_scale=['#EF4444', '#F59E0B', '#10B981'],
            range_color=[0, 150]
        )
        fig2.add_hline(y=100, line_dash="dash", line_color="green", 
                      annotation_text="100%目标线")
        fig2.update_layout(height=400)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("暂无顾问利润数据")


def render_kpi_dashboard():
    """渲染KPI仪表板"""
    st.markdown('<div class="main-header">🎯 KPI 仪表板</div>', unsafe_allow_html=True)
    
    analyzer = st.session_state.analyzer
    kpi = analyzer.get_kpi_dashboard()
    
    # KPI卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #3B82F6;">
            <div style="font-size: 2.5rem; font-weight: bold; color: #3B82F6;">{kpi['deal_count']}</div>
            <div style="font-size: 1rem; color: #6B7280;">累计成单数</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #8B5CF6;">
            <div style="font-size: 2.5rem; font-weight: bold; color: #8B5CF6;">{kpi['avg_fee_rate']:.1f}%</div>
            <div style="font-size: 1rem; color: #6B7280;">平均费率</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #F59E0B;">
            <div style="font-size: 2.5rem; font-weight: bold; color: #F59E0B;">{kpi['avg_collection_days']:.0f}</div>
            <div style="font-size: 1rem; color: #6B7280;">平均回款周期(天)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #10B981;">
            <div style="font-size: 2.5rem; font-weight: bold; color: #10B981;">{kpi['client_retention']:.1f}%</div>
            <div style="font-size: 1rem; color: #6B7280;">客户复购率</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 最佳顾问
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 20px; border-radius: 15px; color: white; text-align: center;">
        <div style="font-size: 1.2rem; opacity: 0.9;">🏆 本月最佳顾问</div>
        <div style="font-size: 2.5rem; font-weight: bold;">{kpi['top_consultant']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 成单明细
    st.markdown('<div class="section-header">📋 成单明细</div>', unsafe_allow_html=True)
    
    if analyzer.deals:
        deals_df = pd.DataFrame([{
            '成单ID': d.deal_id,
            '客户': d.client_name,
            '职位': d.position,
            '顾问': d.consultant,
            '成单日期': d.deal_date.strftime('%Y-%m-%d') if d.deal_date else '-',
            '年薪': format_currency(d.annual_salary) if d.annual_salary > 0 else '-',
            '费率': f"{d.fee_rate}%" if d.fee_rate != 20 else '-',
            '佣金': format_currency(d.fee_amount),
            '回款状态': d.payment_status,
            '实际回款(总)': format_currency(d.actual_payment),
            '其中：上年遗留': format_currency(d.prior_year_collection) if (d.prior_year_collection or 0) > 0 else '-',
            '其中：本年回款': format_currency((d.actual_payment or 0) - (d.prior_year_collection or 0))
        } for d in sorted(analyzer.deals, key=lambda x: x.deal_date, reverse=True)])
        
        # 筛选
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_consultant = st.multiselect("筛选顾问", options=deals_df['顾问'].unique())
        with col2:
            filter_client = st.multiselect("筛选客户", options=deals_df['客户'].unique())
        with col3:
            filter_status = st.multiselect("筛选回款状态", options=deals_df['回款状态'].unique())
        
        filtered_df = deals_df.copy()
        if filter_consultant:
            filtered_df = filtered_df[filtered_df['顾问'].isin(filter_consultant)]
        if filter_client:
            filtered_df = filtered_df[filtered_df['客户'].isin(filter_client)]
        if filter_status:
            filtered_df = filtered_df[filtered_df['回款状态'].isin(filter_status)]
        
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)
        
        # 数据统计
        st.markdown(f"""
        <div style="display: flex; gap: 20px; margin-top: 20px;">
            <div style="flex: 1; background: #F3F4F6; padding: 15px; border-radius: 10px; text-align: center;">
                <div style="font-size: 1.5rem; font-weight: bold; color: #1E40AF;">{len(filtered_df)}</div>
                <div style="font-size: 0.9rem; color: #6B7280;">显示记录数</div>
            </div>
            <div style="flex: 1; background: #F3F4F6; padding: 15px; border-radius: 10px; text-align: center;">
                <div style="font-size: 1.5rem; font-weight: bold; color: #1E40AF;">
                    {format_currency(sum(analyzer.deals[i].fee_amount for i in range(len(analyzer.deals)) if str(analyzer.deals[i].deal_id) in [str(d) for d in filtered_df['成单ID']]))}
                </div>
                <div style="font-size: 0.9rem; color: #6B7280;">筛选佣金总额</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("暂无成单数据")


def render_forecast_analysis():
    """渲染预测分析页面"""
    st.markdown('<div class="main-header">📈 预测收入分析</div>', unsafe_allow_html=True)
    
    analyzer = st.session_state.analyzer
    
    if not analyzer.forecasts:
        st.info("📊 暂无预测数据，请在侧边栏上传在途单/预测数据")
        st.markdown("""
        **预测数据字段说明：**
        - `forecast_id` / `预测编号` - 预测单编号
        - `client_name` / `客户` - 客户名称
        - `position` / `职位` - 职位名称
        - `consultant` / `顾问` - 负责顾问
        - `estimated_salary` / `预计年薪` - 预计候选人年薪
        - `fee_rate` / `费率` - 费率(%)
        - `estimated_fee` / `预计佣金` - 预计佣金金额（如果直接知道）
        - `success_rate` / `成功率` - 成功率预测(%)
        - `stage` / `阶段` - 当前阶段（初期接触/推荐简历/面试中/offer谈判/待发offer）
        - `expected_close_date` / `预计成交日期` - 预计成交日期
        - `note` / `备注` - 备注说明
        
        **核心公式：**
        - 加权预测收入 = 预计佣金 × 成功率
        """)
        return
    
    # 获取预测汇总
    forecast_summary = analyzer.get_forecast_summary()
    
    # 关键指标卡片
    st.markdown("### 📊 预测汇总")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("在途单数", f"{forecast_summary['total_forecasts']}单")
    with col2:
        st.metric("预计佣金总额", format_currency(forecast_summary['total_estimated_fee']))
    with col3:
        st.metric("加权预测收入", format_currency(forecast_summary['weighted_revenue']))
    with col4:
        st.metric("平均成功率", f"{forecast_summary['avg_success_rate']:.1f}%")
    
    st.markdown("---")
    
    # 顾问预测分析
    st.markdown("### 👥 顾问预测排名")
    consultant_forecast = analyzer.get_forecast_by_consultant()
    if not consultant_forecast.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 顾问预测收入柱状图
            fig = px.bar(
                consultant_forecast,
                x='顾问',
                y=['预计佣金总额', '加权预测收入'],
                barmode='group',
                title='顾问预测收入对比',
                template='plotly_white'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 顾问预测表格
            display_df = consultant_forecast.copy()
            display_df['预计佣金总额'] = display_df['预计佣金总额'].apply(format_currency)
            display_df['加权预测收入'] = display_df['加权预测收入'].apply(format_currency)
            display_df['平均成功率'] = display_df['平均成功率'].apply(lambda x: f"{x:.1f}%")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # 阶段分析
    st.markdown("### 📍 阶段分布")
    stage_forecast = analyzer.get_forecast_by_stage()
    if not stage_forecast.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # 阶段饼图
            fig = px.pie(
                stage_forecast,
                values='加权收入',
                names='阶段',
                title='各阶段预测收入占比',
                template='plotly_white'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 阶段表格
            display_df = stage_forecast.copy()
            display_df['预计佣金'] = display_df['预计佣金'].apply(format_currency)
            display_df['加权收入'] = display_df['加权收入'].apply(format_currency)
            display_df['平均成功率'] = display_df['平均成功率'].apply(lambda x: f"{x:.1f}%")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # 时间线分析
    st.markdown("### 📅 预计成交时间线")
    timeline = analyzer.get_forecast_timeline()
    if not timeline.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=timeline['月份'],
            y=timeline['预计佣金'],
            name='预计佣金',
            marker_color='#3B82F6'
        ))
        fig.add_trace(go.Bar(
            x=timeline['月份'],
            y=timeline['加权收入'],
            name='加权收入',
            marker_color='#10B981'
        ))
        fig.update_layout(
            title='月度预测收入趋势',
            xaxis_title='月份',
            yaxis_title='金额',
            barmode='group',
            template='plotly_white',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无预计成交日期数据")
    
    st.markdown("---")
    
    # 预测明细
    st.markdown("### 📋 预测明细")
    forecast_detail = analyzer.get_forecast_detail()
    
    # 筛选
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_consultant = st.multiselect("筛选顾问", options=forecast_detail['顾问'].unique(), key='forecast_consultant')
    with col2:
        filter_stage = st.multiselect("筛选阶段", options=forecast_detail['阶段'].unique(), key='forecast_stage')
    with col3:
        filter_client = st.multiselect("筛选客户", options=forecast_detail['客户'].unique(), key='forecast_client')
    
    filtered_df = forecast_detail.copy()
    if filter_consultant:
        filtered_df = filtered_df[filtered_df['顾问'].isin(filter_consultant)]
    if filter_stage:
        filtered_df = filtered_df[filtered_df['阶段'].isin(filter_stage)]
    if filter_client:
        filtered_df = filtered_df[filtered_df['客户'].isin(filter_client)]
    
    # 格式化显示
    display_df = filtered_df.copy()
    display_df['预计年薪'] = display_df['预计年薪'].apply(format_currency)
    display_df['预计佣金'] = display_df['预计佣金'].apply(format_currency)
    display_df['加权收入'] = display_df['加权收入'].apply(format_currency)
    display_df['成功率'] = display_df['成功率'].apply(lambda x: f"{x:.0f}%")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # 统计
    total_filtered_fee = filtered_df['预计佣金'].sum()
    total_filtered_weighted = filtered_df['加权收入'].sum()
    st.markdown(f"**筛选统计：** 预计佣金 {format_currency(total_filtered_fee)}，加权收入 {format_currency(total_filtered_weighted)}")


def main():
    """主函数"""
    render_sidebar()
    
    # 主内容区标签页
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 总览", 
        "💰 收入分析", 
        "📉 成本分析", 
        "💹 利润分析",
        "🎯 KPI仪表板",
        "📈 预测分析"
    ])
    
    with tab1:
        render_overview()
    
    with tab2:
        render_revenue_analysis()
    
    with tab3:
        render_cost_analysis()
    
    with tab4:
        render_profit_analysis()
    
    with tab5:
        render_kpi_dashboard()
    
    with tab6:
        render_forecast_analysis()


if __name__ == "__main__":
    main()
