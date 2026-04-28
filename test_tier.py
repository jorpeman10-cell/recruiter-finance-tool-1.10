# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import re

# 问题：Amber组织架构/人选变动的规则文本
text = '收集3个开始计算，3个25元一周;5个50元一周'

# 检查是否有"开始计算"
has_start = '开始计算' in text or '起算' in text
print('has_start:', has_start)

# 解析tier_rules
tiers = []
m = re.findall(r'(\d+)\s*个\s*(\d+)\s*元', text)
print('matches:', m)

# 如果has_start且base_amount=50
# 第一个匹配(3, 25)的bonus应该改为50
base_amount = 50
if has_start and m:
    first_min = float(m[0][0])
    first_bonus = float(m[0][1])
    if first_bonus < base_amount:
        print('修正:', first_min, '个的bonus从', first_bonus, '改为', base_amount)
