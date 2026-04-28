# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, 'advanced_analysis')
from okr_analyzer import OKRConfigManager, OKRCalculator
from gllue_db_client import GllueDBClient
import db_config_manager

# 加载配置
manager = OKRConfigManager()
configs = manager.load_all_configs()
print(f'Loaded {len(configs)} configs')

# 测试计算
db_client = GllueDBClient(db_config_manager.get_gllue_db_config())
calc = OKRCalculator(db_client)

# 计算Lucy的3月奖金
lucy = [c for c in configs if c.consultant_name == 'Lucy'][0]
print(f'\nLucy rules:')
for r in lucy.rules:
    print(f'  {r.indicator_name}: target={r.target_value}, weight={r.weight}')

result = calc.calculate_monthly_bonus(lucy, 2026, 3)
print(f'\nLucy 3月奖金计算结果:')
print(f'  Total bonus: {result.total_bonus}')
for ind in result.indicator_results:
    print(f"  {ind['indicator_name']}: actual={ind['actual_value']}, bonus={ind['calculated_bonus']}")

# 计算所有顾问
print('\n=== 所有顾问3月奖金 ===')
results = calc.calculate_all(configs, 2026, 3)
for r in results:
    print(f"{r.consultant_name}: {r.total_bonus}")
