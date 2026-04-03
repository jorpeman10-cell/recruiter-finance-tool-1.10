import pandas as pd
from datetime import datetime, timedelta

# 读取xlsx文件
df = pd.read_excel('成单数据模板03.xlsx')

# D0063-D0078的数据
df_d0063 = df[df['deal_id'] >= 'D0063']

today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
offer_to_onboard = 30
payment_cycle = 90  # 账期90天
total_days = offer_to_onboard + payment_cycle  # 120天

print(f"Today: {today.strftime('%Y-%m-%d')}")
print(f"Offer to onboard: {offer_to_onboard} days")
print(f"Payment cycle: {payment_cycle} days")
print(f"Total cycle: {total_days} days")
print()

print("D0063-D0078 with 120-day cycle:")
total_fee = 0
in_90d = 0
in_180d = 0

for _, row in df_d0063.iterrows():
    deal_date = row['deal_date']
    fee = row['fee_amount'] if pd.notna(row['fee_amount']) else 0
    total_fee += fee
    
    # 推算回款日期
    est_payment = deal_date + timedelta(days=total_days)
    days_until = (est_payment - today).days
    
    if 0 <= days_until <= 90:
        status = 'IN 90d'
        in_90d += fee
    elif 90 < days_until <= 180:
        status = 'IN 180d'
        in_180d += fee
    elif days_until < 0:
        status = f'PAST ({abs(days_until)} days overdue)'
    else:
        status = f'FUTURE ({days_until} days)'
    
    print(f"  {row['deal_id']}: deal={deal_date.strftime('%Y-%m-%d')}, est_payment={est_payment.strftime('%Y-%m-%d')}, {status}, fee={fee:.0f}")

print()
print(f"Total fee: {total_fee:.0f}")
print(f"In 90d: {in_90d:.0f}")
print(f"In 180d: {in_180d:.0f}")
print(f"Total collectible (90d+180d): {in_90d + in_180d:.0f}")
