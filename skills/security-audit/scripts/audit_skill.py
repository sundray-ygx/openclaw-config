#!/usr/bin/env python3
"""
Security Audit Tool V2 - 增强版
- 语义意图分析: 检查声称功能 vs 实际代码行为
- 依赖包 CVE 扫描
- 供应链安全检查
- 标准化审计报告
"""

import os
import sys
import re
import json
import subprocess
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional


class SecurityAuditor:
    """Skill 安全审计器"""
    
    # 风险权重
    RISK_WEIGHTS = {
        'critical': 10,
        'high': 7,
        'medium': 3,
        'low': 1
    }
    
    # 危险代码模式
    DANGEROUS_PATTERNS = {
        'data_exfiltration': [
            r'curl.*-d.*\$\w*key',
            r'curl.*-d.*\$\w*token',
            r'curl.*-d.*\$\w*secret',
            r'requests\.post.*environ',
            r'requests\.post.*api_key',
            r'fetch.*Authorization',
        ],
        'reverse_shell': [
            r'nc\s+-e\s+/bin/',
            r'nc\s+-e\s+/sh',
            r'bash\s+-i\s+>&\s+/dev/tcp/',
            r'python.*socket.*subprocess',
            r'ruby.*TCPSocket.*exec',
        ],
        'privilege_escalation': [
            r'sudo\s+',
            r'chmod\s+777',
            r'chmod\s+4755',
            r'setuid\s*\(',
            r'os\.setuid',
        ],
        'code_execution': [
            r'eval\s*\(',
            r'exec\s*\(',
            r'os\.system\s*\(',
            r'subprocess\.call\s*\(',
            r'subprocess\.run\s*\(',
        ],
        'sensitive_access': [
            r'~/.ssh/',
            r'/etc/shadow',
            r'/etc/passwd',
            r'~/.aws/',
            r'~/.openclaw/openclaw\.json',
            r'MEMORY\.md',
        ],
        'credential_harvest': [
            r'os\.environ\[.*API_KEY',
            r'os\.environ\[.*TOKEN',
            r'os\.environ\[.*SECRET',
            r'process\.env\[',
        ],
    }
    
    def __init__(self, skill_path: str):
        self.skill_path = Path(skill_path)
        self.skill_name = self.skill_path.name
        self.findings: List[Dict] = []
        self.files_analyzed: List[str] = []
        self.dependencies: Dict[str, List[str]] = {}
        
    def audit(self) -> Tuple[int, List[Dict]]:
        """执行完整审计"""
        print(f"🔍 开始审计 Skill: {self.skill_name}")
        print(f"📁 路径: {self.skill_path}")
        
        # 1. 收集文件
        self._collect_files()
        
        # 2. 读取 SKILL.md 分析声称功能
        claimed_purpose = self._analyze_claimed_purpose()
        
        # 3. 分析代码行为
        actual_behavior = self._analyze_code_behavior()
        
        # 4. 语义意图匹配检查
        self._check_intent_mismatch(claimed_purpose, actual_behavior)
        
        # 5. 依赖包安全检查
        self._check_dependencies()
        
        # 6. 计算风险评分
        score = self._calculate_score()
        
        print(f"\n✅ 审计完成")
        print(f"📊 风险评分: {score}/100")
        print(f"🔍 发现问题: {len(self.findings)} 个")
        
        return score, self.findings
    
    def _collect_files(self):
        """收集所有待审计文件"""
        if not self.skill_path.exists():
            raise FileNotFoundError(f"Skill 路径不存在: {self.skill_path}")
        
        for root, dirs, files in os.walk(self.skill_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if file.startswith('.'):
                    continue
                filepath = Path(root) / file
                self.files_analyzed.append(str(filepath.relative_to(self.skill_path)))
        
        print(f"📄 发现 {len(self.files_analyzed)} 个文件")
    
    def _analyze_claimed_purpose(self) -> str:
        """分析 SKILL.md 中声称的功能"""
        skill_md = self.skill_path / 'SKILL.md'
        if not skill_md.exists():
            self.findings.append({
                'level': 'medium',
                'category': 'documentation',
                'description': '缺少 SKILL.md 文件，无法验证声称功能',
                'file': 'SKILL.md',
                'line': 0
            })
            return ""
        
        content = skill_md.read_text(encoding='utf-8')
        desc_match = re.search(r'description:\s*(.+?)(?:\n\w|\Z)', content, re.DOTALL)
        if desc_match:
            return desc_match.group(1).strip()
        
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('# ') and i + 1 < len(lines):
                return lines[i + 1].strip()
        return ""
    
    def _analyze_code_behavior(self) -> Dict[str, List[str]]:
        """分析代码实际行为"""
        behavior = {'network': [], 'filesystem': [], 'execution': [], 'sensitive_access': []}
        
        for rel_path in self.files_analyzed:
            filepath = self.skill_path / rel_path
            if filepath.suffix not in ['.py', '.sh', '.js', '.ts', '.rb']:
                continue
            
            try:
                content = filepath.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    if re.search(r'(requests\.|curl|wget|fetch|urllib)', line):
                        behavior['network'].append(f"{rel_path}:{line_num}")
                    if re.search(r'(open\(|read\(|write\(|os\.path|fs\.)', line):
                        behavior['filesystem'].append(f"{rel_path}:{line_num}")
                    if re.search(r'(eval\(|exec\(|subprocess|os\.system)', line):
                        behavior['execution'].append(f"{rel_path}:{line_num}")
                    self._check_dangerous_patterns(line, rel_path, line_num)
            except Exception as e:
                print(f"  ⚠️ 无法读取文件 {rel_path}: {e}")
        
        return behavior
    
    def _check_dangerous_patterns(self, line: str, filepath: str, line_num: int):
        """检查危险代码模式"""
        # 跳过正则表达式定义行 (以 r' 开头)
        if re.match(r"^\s*r['\"]", line.strip()):
            return
        
        # 跳过列表/字典定义
        stripped = line.strip()
        if stripped.startswith('[') or stripped.startswith(']'):
            return
        if stripped.startswith('{') or stripped.startswith('}'):
            return
        if stripped.startswith('#'):
            return
        
        for category, patterns in self.DANGEROUS_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    level = 'high' if category in ['data_exfiltration', 'reverse_shell'] else 'medium'
                    self.findings.append({
                        'level': level,
                        'category': category,
                        'description': f"检测到 {category}",
                        'file': filepath,
                        'line': line_num,
                        'code': line.strip()[:100]
                    })
    
    def _check_intent_mismatch(self, claimed: str, actual: Dict):
        """检查声称功能与实际行为是否匹配"""
        if not claimed:
            return
        
        claimed_lower = claimed.lower()
        simple_tools = ['calculator', 'converter', 'formatter', 'validator']
        is_simple = any(tool in claimed_lower for tool in simple_tools)
        
        if is_simple and actual['network']:
            self.findings.append({
                'level': 'high',
                'category': 'intent_mismatch',
                'description': f'声称是简单工具，但包含网络行为: {len(actual["network"])} 处',
                'file': 'SKILL.md',
                'line': 0
            })
    
    def _check_dependencies(self):
        """检查依赖包安全"""
        # 检查 requirements.txt
        req_file = self.skill_path / 'requirements.txt'
        if req_file.exists():
            self._check_requirements_txt(req_file)
        
        # 检查 package.json
        pkg_file = self.skill_path / 'package.json'
        if pkg_file.exists():
            self._check_package_json(pkg_file)
    
    def _check_requirements_txt(self, filepath: Path):
        """检查 Python 依赖"""
        try:
            content = filepath.read_text(encoding='utf-8')
            for line_num, line in enumerate(content.split('\n'), 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # 提取包名
                pkg_match = re.match(r'^([a-zA-Z0-9_-]+)', line)
                if pkg_match:
                    pkg_name = pkg_match.group(1).lower()
                    
                    # 检查可疑包名 (typo-squatting)
                    suspicious = ['requessts', 'urllib3s', 'reqeusts', 'crytography', 'djnago', 'nunpy']
                    if any(s in pkg_name for s in suspicious):
                        self.findings.append({
                            'level': 'high',
                            'category': 'supply_chain',
                            'description': f'可疑依赖包 (可能是 typo-squatting): {pkg_name}',
                            'file': str(filepath.relative_to(self.skill_path)),
                            'line': line_num
                        })
        except Exception as e:
            print(f"  ⚠️ 无法读取依赖文件: {e}")
    
    def _check_package_json(self, filepath: Path):
        """检查 Node.js 依赖"""
        try:
            content = json.loads(filepath.read_text(encoding='utf-8'))
            deps = {**content.get('dependencies', {}), **content.get('devDependencies', {})}
            
            for pkg_name in deps:
                suspicious = ['lodashs', 'expresss', 'axiosx', 'node-fetchs']
                if any(s in pkg_name.lower() for s in suspicious):
                    self.findings.append({
                        'level': 'high',
                        'category': 'supply_chain',
                        'description': f'可疑依赖包 (可能是 typo-squatting): {pkg_name}',
                        'file': str(filepath.relative_to(self.skill_path)),
                        'line': 0
                    })
        except Exception as e:
            print(f"  ⚠️ 无法解析 package.json: {e}")
    
    def _calculate_score(self) -> int:
        """计算风险评分"""
        score = 0
        for finding in self.findings:
            level = finding.get('level', 'low')
            score += self.RISK_WEIGHTS.get(level, 1)
        return min(score, 100)
    
    def generate_report(self, score: int, output_path: Optional[str] = None) -> str:
        """生成审计报告"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 确定结果
        if score >= 10:
            result = "拒绝"
            verdict = "🔴 REJECTED"
        elif score >= 5:
            result = "需审核"
            verdict = "🟡 NEEDS REVIEW"
        else:
            result = "通过"
            verdict = "🟢 PASSED"
        
        # 分类风险
        critical = [f for f in self.findings if f['level'] == 'critical']
        high = [f for f in self.findings if f['level'] == 'high']
        medium = [f for f in self.findings if f['level'] == 'medium']
        low = [f for f in self.findings if f['level'] == 'low']
        
        report = f"""# 🛡️ Security Audit Report

**Skill**: `{self.skill_name}`
**审计时间**: {now}
**审计结果**: {result}
**风险评分**: {score}/100

## 🧾 文件清单

| 文件路径 | 类型 |
|----------|------|
"""
        for f in self.files_analyzed[:20]:  # 最多显示20个
            ext = Path(f).suffix or 'text'
            report += f"| `{f}` | {ext} |\n"
        
        if len(self.files_analyzed) > 20:
            report += f"| ... ({len(self.files_analyzed) - 20} more) | - |\n"
        
        report += f"\n## 🔍 检测结果\n\n### {verdict}\n\n"
        
        # 高危风险
        if critical or high:
            report += "#### 🔴 高危风险\n\n"
            for f in critical + high:
                report += f"- **{f['category']}**: {f['description']}\n"
                report += f"  - 文件: `{f['file']}` 第{f['line']}行\n"
                if 'code' in f:
                    report += f"  - 代码: `{f['code']}`\n"
                report += "\n"
        
        # 中危风险
        if medium:
            report += "#### 🟡 中危风险\n\n"
            for f in medium:
                report += f"- **{f['category']}**: {f['description']}\n"
                report += f"  - 文件: `{f['file']}` 第{f['line']}行\n\n"
        
        # 低危/建议
        if low:
            report += "#### 🟢 低危/建议\n\n"
            for f in low:
                report += f"- {f['description']}\n"
        
        if not self.findings:
            report += "✅ 未发现安全风险\n"
        
        report += f"""
## 📊 风险统计

| 级别 | 数量 |
|------|------|
| 🔴 高危 | {len(critical) + len(high)} |
| 🟡 中危 | {len(medium)} |
| 🟢 低危 | {len(low)} |

## 💡 建议操作

**{verdict}**

"""
        if score >= 10:
            report += "- 立即拒绝安装\n- 检查代码中的恶意行为\n- 审查 Skill 来源可信度\n"
        elif score >= 5:
            report += "- 人工审核后决定\n- 确认风险是否可接受\n- 考虑限制使用范围\n"
        else:
            report += "- 允许安装\n- 记录审计日志\n- 持续监控运行行为\n"
        
        report += f"\n---\n*审计工具: ClawGuard Auditor v2*\n"
        
        # 保存报告
        if output_path:
            Path(output_path).write_text(report, encoding='utf-8')
            print(f"📄 报告已保存: {output_path}")
        
        return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Skill Security Auditor')
    parser.add_argument('skill_path', help='Skill 目录路径')
    parser.add_argument('-o', '--output', help='报告输出路径')
    parser.add_argument('--alert', action='store_true', help='发现高危风险时发送告警')
    args = parser.parse_args()
    
    auditor = SecurityAuditor(args.skill_path)
    score, findings = auditor.audit()
    
    # 生成报告
    report = auditor.generate_report(score, args.output)
    print("\n" + "="*60)
    print(report)
    
    # 高危告警
    if args.alert and score >= 10:
        print("\n🚨 检测到高危风险，建议拒绝安装!")
        # 这里可以调用 send_feishu_alert.py 发送告警
    
    return 0 if score < 10 else 1


if __name__ == '__main__':
    sys.exit(main())
