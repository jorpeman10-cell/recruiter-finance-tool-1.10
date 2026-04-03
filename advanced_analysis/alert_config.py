#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
预警配置和邮件通知模块
"""

import json
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional


class AlertConfig:
    """预警配置管理"""
    
    DEFAULT_CONFIG = {
        'email_enabled': False,
        'smtp_server': 'smtp.exmail.qq.com',  # 企业微信邮箱示例
        'smtp_port': 465,
        'smtp_username': '',
        'smtp_password': '',  # 注意：实际使用时需要加密存储
        'sender_email': '',
        'recipients': [],  # 接收人列表
        
        # 预警规则阈值
        'alert_rules': {
            'cashflow_danger': 0,  # 现金余额低于此值触发紧急预警
            'cashflow_warning_months': 2,  # 现金不足N个月成本触发警告
            'collection_overdue_days': 1,  # 逾期N天触发催收预警
            'collection_due_days': 7,  # N天内到期触发提醒
            'consultant_loss_threshold': -50000,  # 顾问亏损阈值
        },
        
        # 发送频率
        'send_frequency': 'daily',  # daily, weekly
        'last_send_time': None,
    }
    
    def __init__(self, config_path: str = 'alert_config.json'):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """加载配置"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 尝试解码密码（兼容旧版明文）
                    password = config.get('smtp_password', '')
                    if password:
                        try:
                            import base64
                            decoded = base64.b64decode(password).decode('utf-8')
                            config['smtp_password'] = decoded
                        except Exception:
                            pass  # 解码失败则保持原值（明文兼容）
                    return config
            except Exception as e:
                print(f"加载预警配置失败: {e}")
                return self.DEFAULT_CONFIG.copy()
        return self.DEFAULT_CONFIG.copy()
    
    def save_config(self):
        """保存配置"""
        try:
            import base64
            config_to_save = self.config.copy()
            password = config_to_save.get('smtp_password', '')
            if password:
                config_to_save['smtp_password'] = base64.b64encode(
                    password.encode('utf-8')
                ).decode('utf-8')
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存预警配置失败: {e}")
            return False
    
    def update_config(self, updates: Dict):
        """更新配置"""
        self.config.update(updates)
        return self.save_config()
    
    def get_smtp_config(self) -> Dict:
        """获取SMTP配置"""
        return {
            'server': self.config.get('smtp_server', ''),
            'port': self.config.get('smtp_port', 465),
            'username': self.config.get('smtp_username', ''),
            'password': self.config.get('smtp_password', ''),
            'sender': self.config.get('sender_email', ''),
        }
    
    def get_recipients(self) -> List[str]:
        """获取收件人列表"""
        return self.config.get('recipients', [])
    
    def add_recipient(self, email: str):
        """添加收件人"""
        recipients = self.get_recipients()
        if email not in recipients:
            recipients.append(email)
            self.config['recipients'] = recipients
            self.save_config()
    
    def remove_recipient(self, email: str):
        """移除收件人"""
        recipients = self.get_recipients()
        if email in recipients:
            recipients.remove(email)
            self.config['recipients'] = recipients
            self.save_config()


class AlertSender:
    """预警邮件发送器"""
    
    def __init__(self, config: AlertConfig):
        self.config = config
    
    def test_connection(self) -> tuple:
        """
        测试SMTP连接
        
        Returns:
            (success: bool, message: str)
        """
        smtp_config = self.config.get_smtp_config()
        
        if not all([smtp_config['server'], smtp_config['username'], smtp_config['password']]):
            return False, "SMTP配置不完整，请检查服务器地址、用户名和密码"
        
        try:
            server = smtplib.SMTP_SSL(smtp_config['server'], smtp_config['port'])
            server.login(smtp_config['username'], smtp_config['password'])
            server.quit()
            return True, "连接成功"
        except Exception as e:
            return False, f"连接失败: {str(e)}"
    
    def send_alert_email(self, alerts: List[Dict], subject: str = "猎头财务预警通知") -> tuple:
        """
        发送预警邮件
        
        Args:
            alerts: 预警列表
            subject: 邮件主题
        
        Returns:
            (success: bool, message: str)
        """
        if not self.config.config.get('email_enabled', False):
            return False, "邮件功能未启用"
        
        recipients = self.config.get_recipients()
        if not recipients:
            return False, "没有配置收件人"
        
        smtp_config = self.config.get_smtp_config()
        
        try:
            # 构建邮件内容
            html_content = self._build_alert_html(alerts)
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = smtp_config['sender'] or smtp_config['username']
            msg['To'] = ', '.join(recipients)
            
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # 发送邮件
            server = smtplib.SMTP_SSL(smtp_config['server'], smtp_config['port'])
            server.login(smtp_config['username'], smtp_config['password'])
            server.sendmail(
                smtp_config['sender'] or smtp_config['username'],
                recipients,
                msg.as_string()
            )
            server.quit()
            
            # 更新发送时间
            self.config.config['last_send_time'] = datetime.now().isoformat()
            self.config.save_config()
            
            return True, f"邮件已发送至 {len(recipients)} 位收件人"
            
        except Exception as e:
            return False, f"发送失败: {str(e)}"
    
    def _build_alert_html(self, alerts: List[Dict]) -> str:
        """构建预警邮件HTML内容"""
        
        # 按级别分组
        danger_alerts = [a for a in alerts if a['level'] == 'danger']
        warning_alerts = [a for a in alerts if a['level'] == 'warning']
        info_alerts = [a for a in alerts if a['level'] == 'info']
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: #1f2937; color: white; padding: 20px; text-align: center; }}
                .summary {{ background: #f3f4f6; padding: 15px; margin: 20px 0; border-radius: 8px; }}
                .alert-section {{ margin: 20px 0; }}
                .alert-danger {{ background: #fee2e2; border-left: 4px solid #ef4444; padding: 15px; margin: 10px 0; }}
                .alert-warning {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 10px 0; }}
                .alert-info {{ background: #dbeafe; border-left: 4px solid #3b82f6; padding: 15px; margin: 10px 0; }}
                .alert-title {{ font-size: 16px; font-weight: bold; margin-bottom: 5px; }}
                .alert-message {{ margin: 5px 0; }}
                .alert-action {{ color: #6b7280; font-size: 14px; margin-top: 5px; }}
                .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔔 猎头财务预警通知</h1>
                <p>{datetime.now().strftime('%Y年%m月%d日 %H:%M')}</p>
            </div>
            
            <div class="summary">
                <h3>预警汇总</h3>
                <p>🔴 紧急: {len(danger_alerts)} 条 | 🟡 警告: {len(warning_alerts)} 条 | 🔵 提示: {len(info_alerts)} 条</p>
            </div>
        """
        
        # 紧急预警
        if danger_alerts:
            html += '<div class="alert-section"><h2>🔴 紧急预警</h2>'
            for alert in danger_alerts:
                html += self._build_alert_card(alert, 'danger')
            html += '</div>'
        
        # 警告预警
        if warning_alerts:
            html += '<div class="alert-section"><h2>🟡 警告</h2>'
            for alert in warning_alerts:
                html += self._build_alert_card(alert, 'warning')
            html += '</div>'
        
        # 提示信息
        if info_alerts:
            html += '<div class="alert-section"><h2>🔵 提示</h2>'
            for alert in info_alerts:
                html += self._build_alert_card(alert, 'info')
            html += '</div>'
        
        html += """
            <div class="footer">
                <p>本邮件由猎头财务分析系统自动生成</p>
                <p>请登录系统查看详细信息</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _build_alert_card(self, alert: Dict, level: str) -> str:
        """构建单个预警卡片"""
        return f"""
        <div class="alert-{level}">
            <div class="alert-title">{alert['title']}</div>
            <div class="alert-message">{alert['message']}</div>
            <div class="alert-action">
                💡 建议: {alert['action']} | 👤 负责人: {alert['responsible']} | 📅 截止: {alert['due_date']}
            </div>
        </div>
        """


# 全局配置实例
_alert_config = None

def get_alert_config() -> AlertConfig:
    """获取预警配置实例（单例）"""
    global _alert_config
    if _alert_config is None:
        _alert_config = AlertConfig()
    return _alert_config
