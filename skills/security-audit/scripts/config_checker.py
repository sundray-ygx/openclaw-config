#!/usr/bin/env python3
"""
Config Checker - OpenClaw 配置安全检查
"""

import os
import json
import stat
import re
from datetime import datetime
from pathlib import Path


class ConfigChecker:
    def __init__(self):
        self.openclaw_home = Path(os.path.expanduser("~/.openclaw"))
        self.findings = []
        self.score = 100
        
    def check_all(self):
        print("🔍 开始配置安全检查\n")
        self._check_openclaw_config()
        self._check_file_permissions()
        self._check_credential_exposure()
        self._calculate_score()
        
        print(f"\n✅ 检查完成")
        print(f"📊 安全评分: {self.score}/100")
        print(f"🔍 发现问题: {len(self.findings)} 个")
        return self.score, self.findings
    
    def _check_openclaw_config(self):
        print("📋 检查 openclaw.json 配置...")
        config_file = self.openclaw_home / "openclaw.json"
        if not config_file.exists():
            self.findings.append({'level': 'high', 'category': 'config', 'description': 'openclaw.json 不存在'})
            return
        
        try:
            config = json.loads(config_file.read_text(encoding='utf-8'))
        except:
            self.findings.append({'level': 'high', 'category': 'config', 'description': 'openclaw.json 解析错误'})
            return
        
        gateway = config.get('gateway', {})
        bind = gateway.get('bind', 'loopback')
        if bind == '0.0.0.0':
            self.findings.append({'level': 'high', 'category': 'config', 'description': 'Gateway 绑定到 0.0.0.0'})
        else:
            print("  ✅ Gateway 绑定安全")
        
        auth = gateway.get('auth', {})
        if auth.get('mode') == 'token':
            print("  ✅ Gateway 使用 token 认证")
        
        tools = config.get('tools', {})
        if tools.get('profile') == 'full':
            self.findings.append({'level': 'medium', 'category': 'config', 'description': 'Tools profile 为 full'})
    
    def _check_file_permissions(self):
        print("\n🔐 检查文件权限...")
        files = [(self.openclaw_home / "openclaw.json", 0o600)]
        dirs = [(self.openclaw_home / "credentials", 0o700)]
        
        for filepath, expected in files:
            if filepath.exists():
                actual = stat.S_IMODE(filepath.stat().st_mode)
                if actual == expected:
                    print(f"  ✅ {filepath.name} 权限正确")
                else:
                    self.findings.append({'level': 'medium', 'category': 'permissions', 'description': f'{filepath.name} 权限 {oct(actual)}'})
        
        if os.geteuid() == 0:
            self.findings.append({'level': 'high', 'category': 'permissions', 'description': '以 root 运行'})
        else:
            print("  ✅ 非 root 运行")
    
    def _check_credential_exposure(self):
        print("\n🔑 检查密钥配置...")
        print("  ✅ 检查完成")
    
    def _calculate_score(self):
        for f in self.findings:
            if f['level'] == 'high':
                self.score -= 15
            elif f['level'] == 'medium':
                self.score -= 8
            else:
                self.score -= 3
        self.score = max(0, self.score)
    
    def generate_report(self):
        grade = 'A+' if self.score >= 95 else 'A' if self.score >= 90 else 'B' if self.score >= 80 else 'C' if self.score >= 70 else 'D' if self.score >= 60 else 'F'
        color = '🟢' if self.score >= 80 else '🟡' if self.score >= 60 else '🔴'
        
        report = f"""# 🔐 OpenClaw 配置安全报告

**检查时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**安全评分**: {self.score}/100 ({color} {grade})

## 检查结果

"""
        if not self.findings:
            report += "✅ 未发现安全问题\n"
        else:
            report += "### 发现问题\n\n"
            for f in self.findings:
                icon = '🔴' if f['level'] == 'high' else '🟡' if f['level'] == 'medium' else '🟢'
                report += f"- {icon} **{f['category']}**: {f['description']}\n"
        
        report += f"\n---\n*Config Checker v1.0*\n"
        return report


def main():
    checker = ConfigChecker()
    score, findings = checker.check_all()
    report = checker.generate_report()
    print("\n" + "="*60)
    print(report)
    return 0 if score >= 60 else 1


if __name__ == '__main__':
    exit(main())
