# T-STAR 猎头财务分析工具 - Skill 文档

**版本: v1.10** | **发布日期: 2026-04-26**

## 项目概述

T-STAR 猎头财务分析工具是一款面向猎头公司的综合经营分析平台，通过直连 Gllue ATS 数据库，实现从现金流安全到顾问产能、从项目新增到组织架构 Mapping 的全方位数据分析。

---

## 10 大核心模块 Skill 总结

### 1. 💰 现金流安全分析 (Cashflow Safety)
**文件**: `models.py` + `app.py:render_dashboard()`

**核心能力**:
- 基于历史回款数据预测未来 90/180 天现金流
- 现金储备安全天数计算（当前余额 ÷ 月均成本）
- 逾期账款双维度计算（35天 Invoice Added + 合同账期）
- 关键指标：现金储备、月固定成本、90天预计余额、安全天数

**数据口径**:
- `invoiceassignment.revenue` = 个人实际分配金额
- `offersign.revenue` = 总职位费用
- 逾期 = Invoice Added ≥35天 且 超过合同账期

**Skill 要点**:
```python
# 现金流安全分析核心公式
safety_days = cash_reserve / monthly_cost
balance_90d = cash_reserve + future_90d_collected + forecast_90d - 3_month_cost
```

---

### 2. 📊 顾问盈亏分析 (Consultant P&L)
**文件**: `models.py:get_consultant_profit_forecast()` + `app.py:render_consultant_profit()`

**核心能力**:
- 顾问级 P&L：已回款 - 累计成本 = 回款利润
- Offer 余粮计算：累计 Offer 未回款 ÷ 月成本
- Forecast 覆盖率：(Offer 待回 + 90天 Forecast) ÷ 6个月成本
- 风险评级：🔴亏损且余粮不足 / 🟡亏损但有余粮 / 🟡盈利但 Pipeline 不足 / 🟢健康

**数据口径**:
- 已离职顾问：成本=0，保留已回款，Offer 待回=0
- 未配置顾问：已过滤不显示
- 平均余粮只计算在职人员

**Skill 要点**:
```python
# 核心指标
actual_profit = actual_collected - cost
offer_reserve_months = offer_pending_total / monthly_cost
forecast_coverage = (offer_pending + forecast_90d) / (monthly_cost * 6)
```

---

### 3. 🎯 顾问绩效行为分析 (Performance Funnel)
**文件**: `consultant_performance.py` + `app.py:render_consultant_performance()`

**核心能力**:
- 漏斗分析：简历推荐(cvsent) → 面试(clientinterview) → Offer(offersign) → 入职(onboard)
- 行为画像分类：⭐高产高转 / 📊高产低转 / 🎯低产高转 / ⚠️低产低转
- Pipeline 健康度：各阶段分布 + 加权收入

**数据口径修正**:
- **简历推荐 = `cvsent`**（不是 `jobsubmission`）
- `offersign` 连表需通过 `jobsubmission` 中间表：`offersign → jobsubmission → joborder`

**Skill 要点**:
```python
# 正确的数据表关联
offer_query = """
    SELECT os.*, u.name 
    FROM offersign os
    LEFT JOIN user u ON os.user_id = u.id
    LEFT JOIN jobsubmission js ON os.jobsubmission_id = js.id  -- 关键中间表
    LEFT JOIN joborder jo ON js.joborder_id = jo.id
"""
```

---

### 4. 📋 项目新增分析 (Project Growth)
**文件**: `consultant_project_analysis.py` + `app.py:render_consultant_project_analysis()`

**核心能力**:
- 顾问/团队维度的项目新增统计
- **工作饱和度评分**（0-100）：项目数(25) + 活跃率(20) + 客户覆盖(20) + 项目金额(25)
- **客户维护度评分**（0-100）：复购率(50) + 新客户开发(50)
- 历史 Offer 金额 vs 当前 Forecast Pipeline 对比

**评分标准**:
| 维度 | 权重 | 阈值 |
|------|------|------|
| 月均项目数 | 25分 | ≥8→25; ≥5→20; ≥3→15; ≥1→10 |
| 活跃项目占比 | 20分 | ≥70%→20; ≥50%→15; ≥30%→10 |
| 客户覆盖度 | 20分 | ≥12家→20; ≥8→16; ≥5→12 |
| 月均Offer金额 | 25分 | ≥15万→25; ≥8万→20; ≥4万→15 |

**Skill 要点**:
```python
# Pipeline/历史比 = 当前Forecast金额 ÷ 近1年历史Offer金额
pipeline_ratio = forecast_revenue / historical_offer_revenue
# >1.0: Pipeline充裕; 0.5-1.0: 接近历史; <0.5: Pipeline不足
```

---

### 5. 📈 Forecast 预测分析 (Forecast Pipeline)
**文件**: `models.py` + `app.py:render_forecast_analysis()`

**核心能力**:
- 在途单加权预期价值计算
- 阶段成功率映射：Shortlist(10%) → 1st(25%) → 2nd(30%) → Final(50%) → Offer(80%) → Onboard(100%)
- 回款日期推算：Offer时间 + 入职天数 + 账期

**Skill 要点**:
```python
STAGE_SUCCESS_RATES = {
    'shortlist': 0.10, '1st': 0.25, '2nd': 0.30,
    '3rd': 0.40, 'final': 0.50, 'offer': 0.80, 'onboard': 1.00
}
weighted_revenue = forecast_fee * success_rate
```

---

### 6. 📅 现金流日历 (Cashflow Calendar)
**文件**: `models.py:_build_auto_cashflow_events()` + `app.py:render_cashflow_calendar()`

**核心能力**:
- 自动生成现金流事件（基于职位数据和成本配置）
- 半月汇总现金流预测
- 逾期账款明细展示

---

### 7. 🔮 情景模拟 (What-if Simulator)
**文件**: `app.py:render_whatif_simulator()`

**核心能力**:
- 模拟1：成本削减（降薪/裁员对现金流的影响）
- 模拟2：回款加速（催收对 180 天余额的改善）
- 实时计算覆盖月数变化

---

### 8. 🔔 智能预警 (Alert System)
**文件**: `alert_page.py` + `alert_config.py`

**核心能力**:
- 现金流预警：余额 < 3个月成本
- 逾期预警：超期账款金额/笔数
- Pipeline 预警：Forecast 覆盖率 < 50%
- 可配置预警阈值和通知方式

---

### 9. 📒 财务状况分析 (Real Finance)
**文件**: `pages/real_finance_page.py` + `real_finance.py`

**核心能力**:
- 基于实际工资/报销/固定成本的精确财务核算
- 与假设模式（3倍工资估算）对比
- 三年财报趋势分析
- 权限保护（需密码进入）

---

### 10. 🗺️ Mapping 组织架构分析 (Org Chart Quality)
**文件**: `mapping_analyzer.py` + `app.py:render_mapping_analysis()`

**核心能力**:
- 解析 `companyorganizationmapping` JSON 数据
- 节点自动分类：人名/部门/职位/低质数据/描述性文字
- **质量评分**（0-100）：100 - 低质节点×5 - 描述节点×2
- 录入人质量排名 + 整改建议自动生成
- 与系统候选人数据库匹配（按名字+Title+电话）

**数据表结构**:
```
companyorganization (文档头) ←→ companyorganizationmapping (JSON内容)
JSON格式: {"roots": [{"text": "姓名", "note": "职位", "children": [...]}]}
```

**Skill 要点**:
```python
# 节点分类规则
if text in ['subtopic', 'topic']: → '低质数据-模板残留'
if len(text) > 40: → '描述性文字'
if re.match(r'^[A-Z]{2,6}$', text): → '职位缩写'
if has_chinese and len(cn_chars) <= 8: → '人名-中英文'
```

---

## 数据库连接 Skill（通用化沉淀）

### 架构设计
**文件**: `gllue_db_client.py` + `db_config_manager.py`

**核心设计**:
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Streamlit UI   │────→│ db_config_manager │────→│  JSON 配置文件  │
│  (密码输入框)    │     │ (base64编码存储)  │     │  (安全持久化)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │ GllueDBConfig    │
                       │ (dataclass配置)   │
                       └──────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
       ┌─────────────┐                 ┌─────────────┐
       │ 直接连接模式 │                 │ SSH隧道模式  │
       │ SQLAlchemy  │                 │ paramiko    │
       │ engine      │                 │ + mysql cli │
       └─────────────┘                 └─────────────┘
```

### 连接模式选择

**模式1: 直接连接**（应用与数据库同服务器）
```python
config = GllueDBConfig(
    db_type="mysql",
    host="127.0.0.1",
    port=3306,
    database="gllue",
    username="debian-sys-maint",
    password="xxx",
    use_ssh=False
)
client = GllueDBClient(config)
df = client.query("SELECT * FROM joborder LIMIT 10")
```

**模式2: SSH 隧道**（远程连接，当前使用）
```python
config = GllueDBConfig(
    db_type="mysql",
    host="127.0.0.1",      # 数据库在SSH服务器本地
    port=3306,
    database="gllue",
    username="debian-sys-maint",
    password="xxx",
    use_ssh=True,
    ssh_host="118.190.96.172",
    ssh_port=9998,          # 非标准SSH端口
    ssh_user="root",
    ssh_password="xxx"
)
```

### SSH 查询实现要点

```python
def _query_via_ssh(self, sql: str) -> pd.DataFrame:
    """SSH 远程执行 SQL 的核心实现"""
    import paramiko, uuid
    
    # 1. 建立 SSH 连接
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        self.config.ssh_host,
        port=self.config.ssh_port,
        username=self.config.ssh_user,
        password=self.config.ssh_password,
        timeout=30
    )
    
    # 2. SQL 写入临时文件（避免引号转义问题）
    tmp_file = f"/tmp/query_{uuid.uuid4().hex}.sql"
    sftp = client.open_sftp()
    with sftp.file(tmp_file, "w") as f:
        f.write(sql)
    sftp.close()
    
    # 3. 通过 mysql cli 执行（比 Python 驱动更稳定）
    cmd = f"mysql -u {user} --password='{pwd}' -D {db} < {tmp_file}"
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    
    # 4. 清理
    client.exec_command(f"rm -f {tmp_file}")
    client.close()
    
    # 5. 解析 tab 分隔输出
    df = pd.read_csv(StringIO(out), sep='\t', engine='python', on_bad_lines='skip')
    return df
```

### 踩坑记录

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| SSH 密码含全角`！` | 输入法切换 | 统一使用半角 `!` |
| 中文乱码 | Windows GBK vs UTF-8 | `decode('utf-8', errors='replace')` |
| Tab 分隔解析失败 | 字段内容含换行/tab | `engine='python', on_bad_lines='skip'` |
| 大数据量超时 | SSH 连接不稳定 | 分批查询 + 本地缓存 |
| 密码明文存储 | 安全要求 | base64 混淆（非加密）+ 文件权限控制 |

### 配置持久化

```python
# db_config_manager.py 核心逻辑
CONFIG_FILE = "config/db_config.json"

def save_db_config(config: dict) -> bool:
    # 密码 base64 编码（混淆级别）
    save_config['password'] = base64.b64encode(password.encode()).decode()
    json.dump(save_config, f)

def load_db_config() -> dict:
    config = json.load(f)
    # 解码密码
    config['password'] = base64.b64decode(config['password'].encode()).decode()
    return config
```

---

## 快速对接新数据库指南

### 步骤1: 确认连接模式
```python
# 本地数据库
db_type = "mysql"  # 或 "postgresql"
use_ssh = False

# 远程数据库（通过跳板机）
use_ssh = True
ssh_host = "跳板机IP"
ssh_port = 22  # 或自定义端口
```

### 步骤2: 测试连接
```python
from gllue_db_client import GllueDBClient, GllueDBConfig

config = GllueDBConfig(
    db_type="mysql",
    host="127.0.0.1",
    port=3306,
    database="your_db",
    username="your_user",
    password="your_pass",
    use_ssh=False
)

client = GllueDBClient(config)
assert client.test_connection(), "连接失败"
```

### 步骤3: 探索表结构
```python
# 列出所有表
tables = client.query("SHOW TABLES")

# 查看表结构
columns = client.query("SHOW COLUMNS FROM your_table")

# 查看样本数据
sample = client.query("SELECT * FROM your_table LIMIT 5")
```

### 步骤4: 封装分析模块
参照 `consultant_project_analysis.py` 或 `mapping_analyzer.py` 的模式：
1. 定义 `Analyzer` 类，接收 `db_client`
2. `load_from_db()` 方法加载数据
3. 多个 `get_xxx()` 分析方法返回 DataFrame
4. 在 `app.py` 中新增 `render_xxx()` 函数渲染 UI

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 UI | Streamlit 1.56.0 |
| 数据可视化 | Plotly + Matplotlib |
| 数据处理 | Pandas 3.0.2 + NumPy |
| 数据库 | MySQL (pymysql/SQLAlchemy) |
| SSH 连接 | Paramiko |
| PDF 报告 | fpdf2 |
| 字体 | Microsoft YaHei / SimHei |

---

## 文件结构

```
recruiter_finance_tool/
├── advanced_analysis/
│   ├── app.py                    # Streamlit 主应用（10个标签页）
│   ├── models.py                 # 核心财务模型（现金流、顾问P&L、Forecast）
│   ├── gllue_db_client.py        # 数据库客户端（直连+SSH双模式）
│   ├── db_config_manager.py      # 安全配置管理（base64编码）
│   ├── consultant_performance.py # 顾问绩效漏斗分析
│   ├── consultant_project_analysis.py  # 项目新增+饱和度评分
│   ├── mapping_analyzer.py       # Mapping组织架构质量分析
│   ├── pdf_report.py             # 股东报告PDF生成
│   ├── alert_page.py             # 智能预警系统
│   ├── pages/
│   │   └── real_finance_page.py  # 财务状况分析（密码保护）
│   └── config/
│       └── db_config.json        # 数据库配置（编码存储）
├── watched/consultants/          # 顾问配置文件（Excel）
├── mapping_history/              # Mapping月度历史数据
└── SKILL.md                      # 本文件
```
