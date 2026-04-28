# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, 'advanced_analysis')
from okr_analyzer import OKRDataStore, OKRCalculator, OKRParser

# 解析Excel
store = OKRDataStore()
consultants = store.parse_and_save('D:/win设备桌面/2025年业绩核算/OKR 记录/OKR-2026.3.xlsx')
print(f'Parsed {len(consultants)} consultants')

# 显示Lucy的规则
lucy = [c for c in consultants if c.name == 'Lucy'][0]
print(f'\nLucy rules:')
for r in lucy.rules:
    print(f'  {r.name}: target={r.target_desc}, weight={r.weight}')
    print(f'    score_rules={r.score_rules}')
    print(f'    thresholds: no={r.threshold_no_bonus}, half={r.threshold_half_bonus}, full={r.threshold_full_bonus}')

# 测试计算
from gllue_db_client import GllueDBClient
import db_config_manager
db_client = GllueDBClient(db_config_manager.get_gllue_db_config())
calc = OKRCalculator(db_client)

result = calc.calculate(lucy, 2026, 3)
print(f'\nLucy 3月奖金: {result["total_bonus"]}')
for r in result['rules']:
    print(f'  {r["name"]}: actual={r["actual"]}, bonus={r["bonus"]}')
    print(f'    {r["detail"]}')
